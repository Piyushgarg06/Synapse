"""Tests for Phase 6: Exports (JSON, Markdown, ZIP).

GATE 6 requirements:
- Parse exported JSON and assert required keys.
- Run zipfile.testzip() to validate ZIP integrity.
- Assert exact member list (flat safe member names, no secrets, no .git, no .synapse/index.db).
- Prove determinism by exporting twice and comparing bytes.
- Show sample of each export.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import zipfile
import pytest

from synapse.core import init_synapse, run_index, get_db_path
from synapse.index.store import IndexDB
from synapse.export.exporter import export_json, export_markdown, export_zip


def _create_export_test_repo() -> str:
    """Create a temporary git repository with Python, JS, and TS files."""
    tmpdir = tempfile.mkdtemp(prefix="synapse_phase6_")
    subprocess.run(["git", "init", tmpdir], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True, check=True)

    with open(os.path.join(tmpdir, "main.py"), "w") as f:
        f.write('''def calculate_total(items):
    return sum(items)

class Invoice:
    def __init__(self, amount):
        self.amount = amount
''')

    with open(os.path.join(tmpdir, "app.js"), "w") as f:
        f.write('''export function renderApp() {
    return "App Rendered";
}
''')

    subprocess.run(["git", "-C", tmpdir, "add", "-A"], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "commit", "-m", "Initial commit"], capture_output=True, check=True)
    return tmpdir


class TestExports:
    """Test JSON, Markdown, and ZIP export generation and validation."""

    def test_export_json_validity_and_schema(self):
        """Exported JSON must contain required top-level keys and valid structured data."""
        repo = _create_export_test_repo()
        try:
            init_synapse(repo)
            run_index(repo)

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                data = export_json(db, repo)

            # Assert required top-level schema keys
            required_keys = {
                "schema_version",
                "checkpoint",
                "files_count",
                "symbols_count",
                "edges_count",
                "references_count",
                "files",
                "symbols",
                "edges",
                "references",
            }
            assert required_keys.issubset(data.keys())

            assert data["schema_version"] == 1
            assert data["files_count"] == 2
            assert data["symbols_count"] >= 3
            assert len(data["files"]) == 2
            assert len(data["symbols"]) >= 3

            # Verify serializable to standard JSON
            json_str = json.dumps(data)
            parsed = json.loads(json_str)
            assert parsed["schema_version"] == 1
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_export_md_determinism_and_content(self):
        """Exported Markdown must be deterministic, byte-identical, and contain structured tables."""
        repo = _create_export_test_repo()
        try:
            init_synapse(repo)
            run_index(repo)

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                md1 = export_markdown(db)
                md2 = export_markdown(db)

            # Determinism: byte-identical output
            assert md1.encode("utf-8") == md2.encode("utf-8")

            # Check sections
            assert "# Synapse Repository Index" in md1
            assert "## Indexed Files" in md1
            assert "## Symbols" in md1
            assert "## Graph Relationships" in md1
            assert "calculate_total" in md1
            assert "renderApp" in md1
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_export_zip_validity_and_members(self):
        """ZIP export must be valid according to testzip(), contain exact safe members, and exclude secrets."""
        repo = _create_export_test_repo()
        try:
            init_synapse(repo)
            run_index(repo)

            zip_path = os.path.join(repo, "test_snapshot.zip")
            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                export_zip(db, zip_path, repo)

            assert os.path.isfile(zip_path)

            with zipfile.ZipFile(zip_path, "r") as zf:
                # 1. zipfile.testzip() returns None if all CRC checksums are valid
                assert zf.testzip() is None

                # 2. Exact member list
                members = sorted(zf.namelist())
                assert members == ["README.txt", "index.json", "index.md"]

                # 3. Ensure no secrets, git internals, or db
                for m in members:
                    assert not m.startswith(".")
                    assert "git" not in m.lower()
                    assert "db" not in m.lower()
                    assert "env" not in m.lower()

                # 4. Verify index.json inside zip is valid JSON
                json_bytes = zf.read("index.json")
                parsed = json.loads(json_bytes.decode("utf-8"))
                assert parsed["schema_version"] == 1

                # 5. Verify index.md inside zip
                md_bytes = zf.read("index.md")
                assert b"# Synapse Repository Index" in md_bytes
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_export_zip_determinism(self):
        """Exporting ZIP twice from the same index must produce byte-identical archives."""
        repo = _create_export_test_repo()
        try:
            init_synapse(repo)
            run_index(repo)

            zip1 = os.path.join(repo, "snap1.zip")
            zip2 = os.path.join(repo, "snap2.zip")

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                export_zip(db, zip1, repo)
                export_zip(db, zip2, repo)

            with open(zip1, "rb") as f1, open(zip2, "rb") as f2:
                bytes1 = f1.read()
                bytes2 = f2.read()

            assert bytes1 == bytes2
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_cli_export_workflow(self):
        """CLI 'synapse export' commands for json, md, and zip write correct files."""
        repo = _create_export_test_repo()
        try:
            init_synapse(repo)
            run_index(repo)

            # JSON export via CLI
            json_out = os.path.join(repo, "out.json")
            subprocess.run(["python", "-m", "synapse.cli", "export", "json", "--output", json_out], cwd=repo, check=True)
            assert os.path.isfile(json_out)
            with open(json_out, "r", encoding="utf-8") as f:
                d = json.load(f)
            assert "schema_version" in d

            # MD export via CLI
            md_out = os.path.join(repo, "out.md")
            subprocess.run(["python", "-m", "synapse.cli", "export", "md", "--output", md_out], cwd=repo, check=True)
            assert os.path.isfile(md_out)
            with open(md_out, "r", encoding="utf-8") as f:
                assert "# Synapse Repository Index" in f.read()

            # ZIP export via CLI
            zip_out = os.path.join(repo, "out.zip")
            subprocess.run(["python", "-m", "synapse.cli", "export", "zip", "--output", zip_out], cwd=repo, check=True)
            assert os.path.isfile(zip_out)
            with zipfile.ZipFile(zip_out, "r") as zf:
                assert zf.testzip() is None
                assert sorted(zf.namelist()) == ["README.txt", "index.json", "index.md"]
        finally:
            shutil.rmtree(repo, ignore_errors=True)
