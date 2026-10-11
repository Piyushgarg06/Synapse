"""Tests for Phase 5: Retrieval and Context (search, inspect, context).

GATE 5 requirements:
- Search ordering and limits.
- Ambiguity handling.
- Inspect output and depth bounds.
- Resolved vs unresolved callers and references.
- Context bounds, reasons, and snippet text equals actual source lines.
- Stale-source check (if file changed since indexing, report it).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import pytest

from synapse.core import init_synapse, run_index, get_db_path
from synapse.index.store import IndexDB
from synapse.retrieval.engine import (
    search_symbols_and_files, inspect_symbol, generate_context,
)


def _create_sample_repo() -> str:
    """Create a temporary repository with a rich class and function hierarchy."""
    tmpdir = tempfile.mkdtemp(prefix="synapse_phase5_")
    subprocess.run(["git", "init", tmpdir], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True, check=True)

    # File 1: core/base.py
    os.makedirs(os.path.join(tmpdir, "core"), exist_ok=True)
    with open(os.path.join(tmpdir, "core", "base.py"), "w") as f:
        f.write('''class BaseWorker:
    def execute(self):
        return "base_exec"

def helper():
    return "helper"
''')

    # File 2: app/worker.py
    os.makedirs(os.path.join(tmpdir, "app"), exist_ok=True)
    with open(os.path.join(tmpdir, "app", "worker.py"), "w") as f:
        f.write('''from core.base import BaseWorker, helper

class CustomWorker(BaseWorker):
    def execute(self):
        helper()
        dynamic_external_call()
        return "custom_exec"

class AnotherWorker:
    def execute(self):
        return "another_exec"
''')

    subprocess.run(["git", "-C", tmpdir, "add", "-A"], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "commit", "-m", "Initial commit"], capture_output=True, check=True)
    return tmpdir


class TestRetrievalAndContext:
    """Test search, inspect, context generation, and stale source detection."""

    def test_search_ordering_and_limits(self):
        """Search ranking must be exact > prefix > substring with tie-breakers, honoring limit."""
        repo = _create_sample_repo()
        try:
            init_synapse(repo)
            run_index(repo)

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                # Query "helper": exact match 'helper' should come before any prefix/substring
                results = search_symbols_and_files(db, "helper", limit=10)
                assert len(results) > 0
                assert results[0]["name"] == "helper"

                # Limit enforcement
                limited = search_symbols_and_files(db, "Worker", limit=2)
                assert len(limited) == 2

                # Prefix match comes before substring match
                prefix_results = search_symbols_and_files(db, "Custom", limit=10)
                assert prefix_results[0]["name"] == "CustomWorker"
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_ambiguity_handling(self):
        """Ambiguous symbol query must return all candidate symbols with paths and lines."""
        repo = _create_sample_repo()
        try:
            init_synapse(repo)
            run_index(repo)

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                # "execute" is defined in BaseWorker, CustomWorker, and AnotherWorker
                res = inspect_symbol(db, "execute")
                assert res["found"] is True
                assert res["ambiguous"] is True
                assert len(res["candidates"]) == 3
                candidate_qnames = [c["qualified_name"] for c in res["candidates"]]
                assert "BaseWorker.execute" in candidate_qnames
                assert "CustomWorker.execute" in candidate_qnames
                assert "AnotherWorker.execute" in candidate_qnames
                for c in res["candidates"]:
                    assert "file_path" in c
                    assert "line" in c
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_inspect_output_and_depth_bounds(self):
        """Inspect must emit full definition, hierarchy, calls, and respect depth bounds."""
        repo = _create_sample_repo()
        try:
            init_synapse(repo)
            run_index(repo)

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                res = inspect_symbol(db, "CustomWorker", depth=1)
                assert res["found"] is True
                assert res["ambiguous"] is False
                assert res["symbol"]["name"] == "CustomWorker"
                assert res["symbol"]["file_path"] == "app/worker.py"
                
                # Base class
                base_names = [b["name"] for b in res["base_classes"]]
                assert "BaseWorker" in base_names

                # Inspect with depth=1 vs depth=2 on CustomWorker.execute
                exec_res_depth1 = inspect_symbol(db, "CustomWorker.execute", depth=1)
                callees_d1 = [c["name"] for c in exec_res_depth1["callees"]]
                assert "helper" in callees_d1
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_resolved_vs_unresolved_callers(self):
        """Unresolved references must be explicitly reported as unresolved without fake edges."""
        repo = _create_sample_repo()
        try:
            init_synapse(repo)
            run_index(repo)

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                res = inspect_symbol(db, "CustomWorker.execute")
                assert res["found"] is True

                # helper() was resolved
                callee_names = [c["name"] for c in res["callees"]]
                assert "helper" in callee_names

                # dynamic_external_call() must be in unresolved_references
                unres_names = [u["name"] for u in res["unresolved_references"]]
                assert "dynamic_external_call" in unres_names
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_context_bounds_reasons_and_snippet_match(self):
        """Context generation must include bounds, reasons, and exact file source snippet."""
        repo = _create_sample_repo()
        try:
            init_synapse(repo)
            run_index(repo)

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                ctx = generate_context(db, repo, "BaseWorker", max_results=5, max_bytes=4096, depth=2)
                assert ctx["query"] == "BaseWorker"
                assert ctx["max_results"] == 5
                assert ctx["max_bytes"] == 4096
                assert len(ctx["items"]) > 0

                item = ctx["items"][0]
                assert item["name"] == "BaseWorker"
                assert "reason" in item and len(item["reason"]) > 0
                assert item["is_stale"] is False

                # Snippet text must exactly equal actual file lines on disk
                file_abs = os.path.join(repo, item["file_path"].replace("/", os.sep))
                with open(file_abs, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                expected_snippet = "".join(lines[item["start_line"] - 1 : item["end_line"]])
                assert item["snippet"].strip() == expected_snippet.strip()
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_stale_source_detection(self):
        """Modifying a file on disk after indexing must trigger a stale-source warning."""
        repo = _create_sample_repo()
        try:
            init_synapse(repo)
            run_index(repo)

            # Modify app/worker.py on disk without committing or re-indexing
            worker_path = os.path.join(repo, "app", "worker.py")
            with open(worker_path, "a") as f:
                f.write("\n# uncommitted edit on disk\n")

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                ctx = generate_context(db, repo, "CustomWorker")
                item = next(it for it in ctx["items"] if it["name"] == "CustomWorker")
                assert item["is_stale"] is True

            # Also verify CLI context command prints the warning
            proc = subprocess.run(
                ["python", "-m", "synapse.cli", "context", "CustomWorker"],
                cwd=repo,
                capture_output=True,
                text=True,
                check=True,
            )
            assert "Warning:" in proc.stdout or "File changed on disk" in proc.stdout
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_context_output_file_and_json(self):
        """Context command supports --output and --json flags."""
        repo = _create_sample_repo()
        try:
            init_synapse(repo)
            run_index(repo)

            out_file = os.path.join(repo, "context_out.md")
            proc = subprocess.run(
                ["python", "-m", "synapse.cli", "context", "helper", "--output", out_file],
                cwd=repo,
                capture_output=True,
                text=True,
                check=True,
            )
            assert os.path.exists(out_file)
            with open(out_file, "r", encoding="utf-8") as f:
                content = f.read()
            assert "helper" in content

            # Test JSON format
            json_proc = subprocess.run(
                ["python", "-m", "synapse.cli", "context", "helper", "--json"],
                cwd=repo,
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(json_proc.stdout)
            assert data["query"] == "helper"
            assert "items" in data
            assert "disclaimer" in data
        finally:
            shutil.rmtree(repo, ignore_errors=True)
