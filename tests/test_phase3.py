"""Tests for Phase 3: Persistence and Knowledge Graph.

GATE 3 requirements:
- Tests prove no duplicate nodes or edges after indexing twice.
- Unique constraints exist in the schema.
- Resolved vs unresolved references is queryable.
- Persistence survives a process restart (a separate subprocess reads the same results).
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import pytest

from synapse.core import init_synapse, run_index, get_db_path
from synapse.index.store import IndexDB
from synapse.models import EdgeType, ReferenceStatus


def _create_multi_file_repo() -> str:
    """Create a multi-file temporary Git repository."""
    tmpdir = tempfile.mkdtemp(prefix="synapse_phase3_")
    subprocess.run(["git", "init", tmpdir], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True, check=True)

    # File 1: base.py
    with open(os.path.join(tmpdir, "base.py"), "w") as f:
        f.write('''class BaseService:
    def execute(self):
        return 42

def global_helper():
    return "ok"
''')

    # File 2: app.py
    with open(os.path.join(tmpdir, "app.py"), "w") as f:
        f.write('''from base import BaseService, global_helper

class AppService(BaseService):
    def run(self):
        self.execute()
        global_helper()
        unknown_external_func()
        return True
''')

    subprocess.run(["git", "-C", tmpdir, "add", "."], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "commit", "-m", "Initial commit"], capture_output=True, check=True)
    return tmpdir


class TestPersistenceAndGraph:
    """Test knowledge graph construction, schema constraints, and persistence."""

    def test_no_duplicate_nodes_or_edges_after_indexing_twice(self):
        """Indexing twice must produce zero duplicate nodes or edges."""
        tmpdir = _create_multi_file_repo()
        try:
            init_synapse(tmpdir)
            
            # First index pass
            ok1, stats1 = run_index(tmpdir)
            assert ok1, stats1

            db_path = get_db_path(tmpdir)
            with IndexDB(db_path) as db:
                nodes_pass1 = db.get_nodes()
                edges_pass1 = db.get_edges()
                node_ids_pass1 = [n["id"] for n in nodes_pass1]
                edge_keys_pass1 = [(e["edge_type"], e["source_id"], e["target_id"]) for e in edges_pass1]

                # Assert no duplicates in pass 1
                assert len(node_ids_pass1) == len(set(node_ids_pass1))
                assert len(edge_keys_pass1) == len(set(edge_keys_pass1))

            # Second index pass (rebuild)
            ok2, stats2 = run_index(tmpdir, rebuild=True)
            assert ok2, stats2

            with IndexDB(db_path) as db:
                nodes_pass2 = db.get_nodes()
                edges_pass2 = db.get_edges()
                node_ids_pass2 = [n["id"] for n in nodes_pass2]
                edge_keys_pass2 = [(e["edge_type"], e["source_id"], e["target_id"]) for e in edges_pass2]

                # Exact same count and no duplicates
                assert len(node_ids_pass2) == len(set(node_ids_pass2))
                assert len(edge_keys_pass2) == len(set(edge_keys_pass2))
                assert len(nodes_pass2) == len(nodes_pass1)
                assert len(edges_pass2) == len(edges_pass1)

                # Check SQL duplicate query directly
                cursor = db.conn.cursor()
                cursor.execute(
                    """SELECT edge_type, source_id, target_id, COUNT(*)
                       FROM edges GROUP BY edge_type, source_id, target_id
                       HAVING COUNT(*) > 1"""
                )
                assert cursor.fetchall() == []

                cursor.execute(
                    """SELECT file_path, qualified_name, kind, ordinal, COUNT(*)
                       FROM symbols GROUP BY file_path, qualified_name, kind, ordinal
                       HAVING COUNT(*) > 1"""
                )
                assert cursor.fetchall() == []
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_unique_constraints_exist_in_schema(self):
        """Schema must enforce unique constraints on files, symbols, and edges."""
        tmpdir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmpdir, "test.db")
            with IndexDB(db_path) as db:
                c = db.conn.cursor()

                # 1. Unique files path
                c.execute("INSERT INTO files (path, language) VALUES ('test.py', 'python')")
                with pytest.raises(sqlite3.IntegrityError):
                    c.execute("INSERT INTO files (path, language) VALUES ('test.py', 'python')")

                # 2. Unique edges (edge_type, source_id, target_id)
                c.execute("INSERT INTO edges (edge_type, source_id, target_id) VALUES ('CALLS', 's1', 's2')")
                with pytest.raises(sqlite3.IntegrityError):
                    c.execute("INSERT INTO edges (edge_type, source_id, target_id) VALUES ('CALLS', 's1', 's2')")

                # 3. Unique symbols (file_path, qualified_name, kind, ordinal)
                c.execute(
                    """INSERT INTO symbols
                       (id, name, qualified_name, kind, file_id, file_path,
                        start_byte, end_byte, start_line, start_column, end_line, end_column, ordinal)
                       VALUES ('sym1', 'fn', 'fn', 'function', 1, 'test.py', 0, 10, 1, 0, 2, 0, 0)"""
                )
                with pytest.raises(sqlite3.IntegrityError):
                    c.execute(
                        """INSERT INTO symbols
                           (id, name, qualified_name, kind, file_id, file_path,
                            start_byte, end_byte, start_line, start_column, end_line, end_column, ordinal)
                           VALUES ('sym2', 'fn', 'fn', 'function', 1, 'test.py', 0, 10, 1, 0, 2, 0, 0)"""
                    )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_resolved_vs_unresolved_is_queryable(self):
        """Resolved vs unresolved references must be queryable and accurately classified."""
        tmpdir = _create_multi_file_repo()
        try:
            init_synapse(tmpdir)
            ok, stats = run_index(tmpdir)
            assert ok, stats

            db_path = get_db_path(tmpdir)
            with IndexDB(db_path) as db:
                resolved = db.get_resolved_references()
                unresolved = db.get_unresolved_references()

                assert len(resolved) > 0
                assert len(unresolved) > 0

                resolved_names = [r["name"] for r in resolved]
                unresolved_names = [r["name"] for r in unresolved]

                # execute, global_helper, and self.execute are resolved
                assert "execute" in resolved_names or "self.execute" in resolved_names
                assert "global_helper" in resolved_names

                # unknown_external_func must be unresolved
                assert "unknown_external_func" in unresolved_names

                # All resolved references must point to valid symbol IDs
                for r in resolved:
                    assert r["status"] == "resolved"
                    assert r["resolved_symbol_id"] is not None
                    sym = db.get_symbol_by_id(r["resolved_symbol_id"])
                    assert sym is not None

                # All unresolved references have status 'unresolved' and NULL symbol_id
                for r in unresolved:
                    assert r["status"] == "unresolved"
                    assert r["resolved_symbol_id"] is None

                # Graph edges: CALLS edges only exist for resolved calls
                calls_edges = db.get_edges(edge_type="CALLS")
                assert len(calls_edges) > 0
                for edge in calls_edges:
                    # Target must be a valid symbol
                    target_sym = db.get_symbol_by_id(edge["target_id"])
                    assert target_sym is not None

                # INHERITS_FROM edge connects AppService to BaseService
                inh_edges = db.get_edges(edge_type="INHERITS_FROM")
                assert len(inh_edges) == 1
                app_sym = db.search_symbols("AppService")[0]
                base_sym = db.search_symbols("BaseService")[0]
                assert inh_edges[0]["source_id"] == app_sym["id"]
                assert inh_edges[0]["target_id"] == base_sym["id"]

                # IMPORTS edge connects app.py to base.py
                imp_edges = db.get_edges(edge_type="IMPORTS")
                assert len(imp_edges) == 1
                assert imp_edges[0]["source_id"] == "file:app.py"
                assert imp_edges[0]["target_id"] == "file:base.py"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_persistence_survives_process_restart(self):
        """A separate subprocess must read identical index data from index.db."""
        tmpdir = _create_multi_file_repo()
        try:
            init_synapse(tmpdir)
            ok, stats = run_index(tmpdir)
            assert ok, stats

            db_path = get_db_path(tmpdir)
            
            # Read state in current process
            with IndexDB(db_path) as db:
                chk = db.get_checkpoint()
                sym_cnt = db.get_symbol_count()
                edge_cnt = db.get_edge_count()
                resolved_cnt = len(db.get_resolved_references())
                unresolved_cnt = len(db.get_unresolved_references())

            # Spawn a separate Python subprocess to query the database
            script = f'''
import json
from synapse.index.store import IndexDB

with IndexDB(r"{db_path}") as db:
    data = {{
        "checkpoint": db.get_checkpoint(),
        "symbols": db.get_symbol_count(),
        "edges": db.get_edge_count(),
        "resolved": len(db.get_resolved_references()),
        "unresolved": len(db.get_unresolved_references()),
    }}
    print(json.dumps(data))
'''
            res = subprocess.run(
                ["python", "-c", script],
                capture_output=True,
                text=True,
                check=True,
            )
            sub_data = json.loads(res.stdout.strip())

            assert sub_data["checkpoint"] == chk
            assert sub_data["symbols"] == sym_cnt
            assert sub_data["edges"] == edge_cnt
            assert sub_data["resolved"] == resolved_cnt
            assert sub_data["unresolved"] == unresolved_cnt
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_replacing_file_cleans_stale_symbols_and_edges(self):
        """Updating a file must delete its old symbols and edges without leaving orphans."""
        tmpdir = _create_multi_file_repo()
        try:
            init_synapse(tmpdir)
            ok, stats = run_index(tmpdir)
            assert ok, stats

            db_path = get_db_path(tmpdir)
            with IndexDB(db_path) as db:
                assert len(db.search_symbols("global_helper")) == 1
                assert len(db.get_edges(edge_type="CALLS")) > 0

            # Overwrite base.py removing global_helper
            with open(os.path.join(tmpdir, "base.py"), "w") as f:
                f.write('''class BaseService:
    def execute(self):
        return 99
''')
            subprocess.run(["git", "-C", tmpdir, "add", "."], capture_output=True, check=True)
            subprocess.run(["git", "-C", tmpdir, "commit", "-m", "Remove global_helper"], capture_output=True, check=True)

            ok, stats = run_index(tmpdir)
            assert ok, stats

            with IndexDB(db_path) as db:
                # global_helper symbol is completely removed
                assert len(db.search_symbols("global_helper")) == 0

                # Any CALLS edge pointing to old global_helper symbol is gone
                calls = db.get_edges(edge_type="CALLS")
                for c in calls:
                    assert db.get_symbol_by_id(c["target_id"]) is not None
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
