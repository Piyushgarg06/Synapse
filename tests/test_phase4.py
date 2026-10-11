"""Tests for Phase 4: Git-aware Incremental Indexing.

GATE 4 requirements:
- Tests for add, modify, delete, rename, no-op, repeated runs.
- Injected failure mid-run (checkpoint and data unchanged afterward).
- Corrupt-state recovery via rebuild.
- Dirty working tree reported in status.
- EQUIVALENCE TEST: incrementally updated index equals a fresh full rebuild of the same HEAD.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import pytest

from synapse.core import init_synapse, run_index, get_status, get_db_path
from synapse.index.store import IndexDB


def _create_git_repo() -> str:
    """Create a temporary git repository."""
    tmpdir = tempfile.mkdtemp(prefix="synapse_phase4_")
    subprocess.run(["git", "init", tmpdir], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True, check=True)
    return tmpdir


def _commit_all(repo_root: str, message: str) -> str:
    """Add all and commit, returning commit SHA."""
    subprocess.run(["git", "-C", repo_root, "add", "-A"], capture_output=True, check=True)
    subprocess.run(["git", "-C", repo_root, "commit", "-m", message], capture_output=True, check=True)
    res = subprocess.run(["git", "-C", repo_root, "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    return res.stdout.strip()


class TestIncrementalIndexing:
    """Test git-aware incremental indexing operations."""

    def test_add_file_incrementally(self):
        """Adding a file updates the index incrementally without reparsing unchanged files."""
        repo = _create_git_repo()
        try:
            with open(os.path.join(repo, "file1.py"), "w") as f:
                f.write("def func1(): return 1\n")
            _commit_all(repo, "Commit 1")

            init_synapse(repo)
            ok, stats = run_index(repo)
            assert ok
            assert stats["files_processed"] == 1
            assert stats["reparsed"] == 1

            # Add file2
            with open(os.path.join(repo, "file2.py"), "w") as f:
                f.write("def func2(): return 2\n")
            c2 = _commit_all(repo, "Commit 2")

            ok, stats = run_index(repo)
            assert ok
            assert stats["mode"] == "incremental"
            assert stats["files_added"] == 1
            assert stats["reparsed"] == 1  # Only file2 was parsed!

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                assert db.get_checkpoint() == c2
                assert len(db.search_symbols("func1")) == 1
                assert len(db.search_symbols("func2")) == 1
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_modify_file_incrementally(self):
        """Modifying a file updates symbols without reparsing unchanged files."""
        repo = _create_git_repo()
        try:
            with open(os.path.join(repo, "file1.py"), "w") as f:
                f.write("def old_func(): return 1\n")
            with open(os.path.join(repo, "file2.py"), "w") as f:
                f.write("def func2(): return 2\n")
            _commit_all(repo, "Commit 1")

            init_synapse(repo)
            ok, stats = run_index(repo)
            assert ok
            assert stats["files_processed"] == 2

            # Modify file1: change old_func to new_func
            with open(os.path.join(repo, "file1.py"), "w") as f:
                f.write("def new_func(): return 100\n")
            c2 = _commit_all(repo, "Commit 2")

            ok, stats = run_index(repo)
            assert ok
            assert stats["mode"] == "incremental"
            assert stats["files_modified"] == 1
            assert stats["reparsed"] == 1  # file2 was NOT reparsed!

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                assert db.get_checkpoint() == c2
                assert len(db.search_symbols("old_func")) == 0
                assert len(db.search_symbols("new_func")) == 1
                assert len(db.search_symbols("func2")) == 1
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_delete_file_incrementally(self):
        """Deleting a file removes its symbols and relationships."""
        repo = _create_git_repo()
        try:
            with open(os.path.join(repo, "file1.py"), "w") as f:
                f.write("def func1(): return 1\n")
            with open(os.path.join(repo, "to_delete.py"), "w") as f:
                f.write("def will_be_deleted(): return 0\n")
            _commit_all(repo, "Commit 1")

            init_synapse(repo)
            run_index(repo)

            # Delete file
            os.remove(os.path.join(repo, "to_delete.py"))
            c2 = _commit_all(repo, "Delete file")

            ok, stats = run_index(repo)
            assert ok
            assert stats["files_deleted"] == 1
            assert stats["reparsed"] == 0

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                assert db.get_checkpoint() == c2
                assert len(db.search_symbols("will_be_deleted")) == 0
                assert len(db.search_symbols("func1")) == 1
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_rename_file_incrementally(self):
        """Renaming a file updates file path without leaving orphaned records."""
        repo = _create_git_repo()
        try:
            with open(os.path.join(repo, "old_name.py"), "w") as f:
                f.write("def special_handler(): return 42\n")
            _commit_all(repo, "Commit 1")

            init_synapse(repo)
            run_index(repo)

            # Rename file using git mv
            subprocess.run(["git", "-C", repo, "mv", "old_name.py", "new_name.py"], check=True)
            c2 = _commit_all(repo, "Rename file")

            ok, stats = run_index(repo)
            assert ok
            assert stats["files_renamed"] == 1

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                assert db.get_checkpoint() == c2
                syms = db.search_symbols("special_handler")
                assert len(syms) == 1
                assert syms[0]["file_path"] == "new_name.py"

                # Check old_name.py does not exist anywhere in database
                c = db.conn.cursor()
                c.execute("SELECT COUNT(*) FROM files WHERE path = 'old_name.py'")
                assert c.fetchone()[0] == 0
                c.execute("SELECT COUNT(*) FROM symbols WHERE file_path = 'old_name.py'")
                assert c.fetchone()[0] == 0
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_no_op_when_unchanged(self):
        """Indexing when repo is unchanged is a no-op with reparsed=0."""
        repo = _create_git_repo()
        try:
            with open(os.path.join(repo, "file1.py"), "w") as f:
                f.write("def func(): return 1\n")
            _commit_all(repo, "Commit 1")

            init_synapse(repo)
            run_index(repo)

            # Re-run index without any git changes
            ok, stats = run_index(repo)
            assert ok
            assert "up to date" in stats["message"].lower()
            assert stats["files_processed"] == 0
            assert stats["reparsed"] == 0
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_injected_failure_mid_run_preserves_checkpoint_and_data(self):
        """If indexing fails mid-transaction, rollback preserves checkpoint and prior state."""
        repo = _create_git_repo()
        try:
            with open(os.path.join(repo, "file1.py"), "w") as f:
                f.write("def stable_func(): return 1\n")
            c1 = _commit_all(repo, "Commit 1")

            init_synapse(repo)
            run_index(repo)

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                assert db.get_checkpoint() == c1
                initial_dump = db.get_normalized_dump()

            # Add file2 and commit
            with open(os.path.join(repo, "file2.py"), "w") as f:
                f.write("def func2(): return 2\n")
            _commit_all(repo, "Commit 2")

            # Monkey-patch synapse.core.analyze_file to raise an error during processing of file2
            import synapse.core
            original_analyze = synapse.core.analyze_file

            def failing_analyze(file_path, repo_root):
                if "file2" in file_path:
                    raise RuntimeError("Injected disk/analyzer failure!")
                return original_analyze(file_path, repo_root)

            synapse.core.analyze_file = failing_analyze
            try:
                ok, stats = run_index(repo)
                assert ok is False
                assert "Injected" in stats["error"]
            finally:
                synapse.core.analyze_file = original_analyze

            # Checkpoint and database must be completely rolled back and unchanged
            with IndexDB(db_path) as db:
                assert db.get_checkpoint() == c1  # Still at c1!
                current_dump = db.get_normalized_dump()
                assert current_dump == initial_dump
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_dirty_working_tree_reported_in_status(self):
        """Uncommitted working tree changes must be detected and reported in status."""
        repo = _create_git_repo()
        try:
            with open(os.path.join(repo, "file1.py"), "w") as f:
                f.write("def clean(): pass\n")
            _commit_all(repo, "Commit 1")

            init_synapse(repo)
            run_index(repo)

            # Initially clean
            status = get_status(repo)
            assert status["dirty_working_tree"] is False
            assert status["up_to_date"] is True

            # Introduce uncommitted change
            with open(os.path.join(repo, "file1.py"), "a") as f:
                f.write("\n# uncommitted comment\n")

            status = get_status(repo)
            assert status["dirty_working_tree"] is True
            assert status["up_to_date"] is False
            assert "uncommitted" in status["warning"].lower()
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_corrupt_state_recovery_via_rebuild(self):
        """Rebuilding from non-ancestor or corrupt checkpoint restores clean index."""
        repo = _create_git_repo()
        try:
            with open(os.path.join(repo, "file1.py"), "w") as f:
                f.write("def func(): return 1\n")
            c1 = _commit_all(repo, "Commit 1")

            init_synapse(repo)
            run_index(repo)

            # Corrupt checkpoint to a non-existent commit SHA
            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                db.set_checkpoint("0123456789abcdef0123456789abcdef01234567")

            # Normal index should refuse with non-ancestor error
            ok, stats = run_index(repo)
            assert ok is False
            assert "rebuild" in stats["error"].lower()

            # Full rebuild should succeed cleanly
            ok, stats = run_index(repo, rebuild=True)
            assert ok is True
            assert stats["mode"] == "rebuild"

            with IndexDB(db_path) as db:
                assert db.get_checkpoint() == c1
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_equivalence_incremental_vs_full_rebuild(self):
        """EQUIVALENCE TEST: Incrementally updated index equals a fresh full rebuild of the same HEAD."""
        repo = _create_git_repo()
        try:
            # Commit 1: Initial files across multiple languages
            with open(os.path.join(repo, "service.py"), "w") as f:
                f.write("class Service:\n    def start(self):\n        return 'started'\n")
            with open(os.path.join(repo, "util.js"), "w") as f:
                f.write("export function format(val) { return val.trim(); }\n")
            with open(os.path.join(repo, "old_helper.py"), "w") as f:
                f.write("def old_helper(): return 1\n")
            _commit_all(repo, "Commit 1")

            init_synapse(repo)
            run_index(repo)

            # Commit 2: Add TS file and modify Python file
            with open(os.path.join(repo, "types.ts"), "w") as f:
                f.write("export interface Config { timeout: number; }\n")
            with open(os.path.join(repo, "service.py"), "a") as f:
                f.write("    def stop(self):\n        return 'stopped'\n")
            _commit_all(repo, "Commit 2")
            run_index(repo)

            # Commit 3: Rename JS file and delete old_helper.py
            subprocess.run(["git", "-C", repo, "mv", "util.js", "format.js"], check=True)
            os.remove(os.path.join(repo, "old_helper.py"))
            final_sha = _commit_all(repo, "Commit 3: rename & delete")

            # Final incremental update to HEAD
            ok, stats = run_index(repo)
            assert ok

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                incremental_dump = db.get_normalized_dump()

            # Now perform a fresh full rebuild on the exact same HEAD
            ok_rebuild, stats_rebuild = run_index(repo, rebuild=True)
            assert ok_rebuild

            with IndexDB(db_path) as db:
                rebuild_dump = db.get_normalized_dump()

            # Both dumps must be 100% IDENTICAL!
            assert incremental_dump["files"] == rebuild_dump["files"]
            assert incremental_dump["symbols"] == rebuild_dump["symbols"]
            assert incremental_dump["edges"] == rebuild_dump["edges"]
            assert incremental_dump["references"] == rebuild_dump["references"]
            assert incremental_dump == rebuild_dump
        finally:
            shutil.rmtree(repo, ignore_errors=True)
