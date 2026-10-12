"""Tests for working-tree indexing and delete-info impact analysis."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import pytest

from synapse.core import init_synapse, run_index, get_status, get_db_path
from synapse.index.store import IndexDB
from synapse.analysis.impact import analyze_file_deletion, analyze_symbol_deletion
from synapse.cli import main


def _create_git_repo() -> str:
    """Create a temporary git repository."""
    tmpdir = tempfile.mkdtemp(prefix="synapse_wt_test_")
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


class TestDeleteInfoImpactAnalysis:
    """Test delete-info blast radius calculations."""

    def test_file_deletion_impact(self):
        repo = _create_git_repo()
        try:
            # File 1: utils
            with open(os.path.join(repo, "utils.py"), "w") as f:
                f.write(
                    "def helper_func():\n"
                    "    return 42\n"
                    "\n"
                    "class BaseHelper:\n"
                    "    def ping(self):\n"
                    "        return 'pong'\n"
                )
            # File 2: app (imports and calls utils)
            with open(os.path.join(repo, "app.py"), "w") as f:
                f.write(
                    "from utils import helper_func, BaseHelper\n"
                    "\n"
                    "class AppService(BaseHelper):\n"
                    "    def run(self):\n"
                    "        val = helper_func()\n"
                    "        return val\n"
                )
            _commit_all(repo, "Initial commit")

            init_synapse(repo)
            ok, stats = run_index(repo)
            assert ok

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                result = analyze_file_deletion(db, "utils.py")

            assert result["found"] is True
            assert result["affected_file_count"] == 1
            assert "app.py" in result["affected_files"]
            assert len(result["symbols_lost"]) >= 2
            assert result["total_broken_links"] > 0
            assert len(result["dependents"]["importers"]) >= 1
            assert len(result["dependents"]["callers"]) >= 1
            assert len(result["dependents"]["subclasses"]) >= 1
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_symbol_deletion_impact_scoped(self):
        repo = _create_git_repo()
        try:
            with open(os.path.join(repo, "calc.py"), "w") as f:
                f.write(
                    "def add(a, b):\n"
                    "    return a + b\n"
                    "\n"
                    "def subtract(a, b):\n"
                    "    return a - b\n"
                )
            with open(os.path.join(repo, "main.py"), "w") as f:
                f.write(
                    "from calc import add\n"
                    "\n"
                    "def calculate():\n"
                    "    return add(1, 2)\n"
                )
            _commit_all(repo, "Initial commit")

            init_synapse(repo)
            run_index(repo)

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                # Target symbol 'add' scoped to 'calc.py'
                result_add = analyze_symbol_deletion(db, "add", file_path="calc.py")
                assert result_add["found"] is True
                assert result_add["affected_file_count"] == 1
                assert "main.py" in result_add["affected_files"]

                # Target symbol 'subtract' - nothing calls it
                result_sub = analyze_symbol_deletion(db, "subtract", file_path="calc.py")
                assert result_sub["found"] is True
                assert result_sub["affected_file_count"] == 0
        finally:
            shutil.rmtree(repo, ignore_errors=True)


class TestWorkingTreeIndexing:
    """Test synapse index --working-tree operations."""

    def test_working_tree_indexes_uncommitted_and_untracked_files(self):
        repo = _create_git_repo()
        try:
            # Commit 1: just a base file
            with open(os.path.join(repo, "base.py"), "w") as f:
                f.write("def base_func(): pass\n")
            _commit_all(repo, "Base commit")

            init_synapse(repo)
            ok, stats = run_index(repo)
            assert ok
            assert stats["symbols_found"] == 1

            # Create an uncommitted, untracked new file
            with open(os.path.join(repo, "uncommitted_new.py"), "w") as f:
                f.write(
                    "from base import base_func\n"
                    "def new_model_func():\n"
                    "    base_func()\n"
                )

            # Standard run_index: working tree changes are ignored
            ok, normal_stats = run_index(repo)
            assert ok
            assert normal_stats["symbols_found"] == 1

            # Run index --working-tree
            ok, wt_stats = run_index(repo, working_tree=True)
            assert ok
            assert wt_stats["symbols_found"] == 2

            # Check that IndexDB now contains the new file's symbol and edge
            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                syms = db.search_symbols("new_model_func")
                assert len(syms) == 1
                assert syms[0]["file_path"] == "uncommitted_new.py"

            # Check status reflects working-tree indexing
            status = get_status(repo)
            assert status["dirty_working_tree"] is True
            assert status.get("working_tree_indexed") is True
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_working_tree_indexes_modified_and_deleted_files(self):
        repo = _create_git_repo()
        try:
            with open(os.path.join(repo, "file_a.py"), "w") as f:
                f.write("def func_a(): return 1\n")
            with open(os.path.join(repo, "file_b.py"), "w") as f:
                f.write("def func_b(): return 2\n")
            _commit_all(repo, "Commit 1")

            init_synapse(repo)
            run_index(repo)

            # Modify file_a without committing: add a new function
            with open(os.path.join(repo, "file_a.py"), "a") as f:
                f.write("def func_a_extra(): return 100\n")

            # Delete file_b from disk without committing
            os.remove(os.path.join(repo, "file_b.py"))

            # Run index --working-tree
            ok, stats = run_index(repo, working_tree=True)
            assert ok

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                # func_a_extra must be found
                assert len(db.search_symbols("func_a_extra")) == 1
                # file_b symbols must have been removed
                assert len(db.search_symbols("func_b")) == 0
                assert db.get_file_count() == 1
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_working_tree_cli_invocation(self):
        repo = _create_git_repo()
        try:
            with open(os.path.join(repo, "mod.py"), "w") as f:
                f.write("def alpha(): pass\n")
            _commit_all(repo, "Initial")

            init_synapse(repo)
            run_index(repo)

            with open(os.path.join(repo, "mod.py"), "a") as f:
                f.write("def beta(): alpha()\n")

            # Run CLI: synapse index --working-tree --json
            old_argv = sys.argv
            old_cwd = os.getcwd()
            try:
                os.chdir(repo)
                sys.argv = ["synapse", "index", "--working-tree", "--json"]
                ret = main()
                assert ret == 0

                # Run CLI: synapse delete-info mod.py alpha
                sys.argv = ["synapse", "delete-info", "mod.py", "alpha"]
                ret = main()
                assert ret == 0
            finally:
                sys.argv = old_argv
                os.chdir(old_cwd)
        finally:
            shutil.rmtree(repo, ignore_errors=True)
