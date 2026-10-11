"""Tests for Synapse init and vertical slice (Phase 1)."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import shutil
import pytest


def _create_temp_git_repo():
    """Create a temporary Git repository with a Python file."""
    tmpdir = tempfile.mkdtemp(prefix="synapse_test_")
    subprocess.run(["git", "init", tmpdir], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True, check=True)
    
    # Create a Python file
    py_file = os.path.join(tmpdir, "hello.py")
    with open(py_file, "w") as f:
        f.write('def greet(name):\n    return f"Hello, {name}!"\n\nclass Greeter:\n    def say_hello(self):\n        return greet("World")\n')
    
    subprocess.run(["git", "-C", tmpdir, "add", "."], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "commit", "-m", "Initial commit"], capture_output=True, check=True)
    
    return tmpdir


def _run_synapse(args: list[str], cwd: str) -> subprocess.CompletedProcess:
    """Run synapse CLI in a directory."""
    return subprocess.run(
        ["python", "-m", "synapse.cli"] + args,
        capture_output=True,
        text=True,
        cwd=cwd,
    )


class TestInit:
    """Test synapse init command."""
    
    def test_init_creates_synapse_dir(self):
        tmpdir = _create_temp_git_repo()
        try:
            from synapse.core import init_synapse
            success, msg = init_synapse(tmpdir)
            assert success, msg
            assert os.path.exists(os.path.join(tmpdir, ".synapse", "index.db"))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_init_repeated_safe(self):
        """Repeated init should not overwrite data."""
        tmpdir = _create_temp_git_repo()
        try:
            from synapse.core import init_synapse
            success1, msg1 = init_synapse(tmpdir)
            assert success1
            
            success2, msg2 = init_synapse(tmpdir)
            assert success2
            assert "already initialized" in msg2.lower() or "preserved" in msg2.lower()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_init_via_cli(self):
        """Test init through CLI subprocess."""
        tmpdir = _create_temp_git_repo()
        try:
            result = _run_synapse(["init"], cwd=tmpdir)
            assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
            assert os.path.exists(os.path.join(tmpdir, ".synapse", "index.db"))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestVerticalSlice:
    """Test the init -> index -> search vertical slice for Python."""
    
    def test_index_python_file(self):
        tmpdir = _create_temp_git_repo()
        try:
            from synapse.core import init_synapse, run_index
            init_synapse(tmpdir)
            
            success, stats = run_index(tmpdir)
            assert success, stats
            assert stats["files_processed"] > 0
            assert stats["symbols_found"] > 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_search_finds_function(self):
        tmpdir = _create_temp_git_repo()
        try:
            from synapse.core import init_synapse, run_index, get_db_path
            from synapse.index.store import IndexDB
            
            init_synapse(tmpdir)
            run_index(tmpdir)
            
            with IndexDB(get_db_path(tmpdir)) as db:
                results = db.search_symbols("greet")
            
            assert len(results) > 0
            names = [r["name"] for r in results]
            assert "greet" in names
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_search_finds_class(self):
        tmpdir = _create_temp_git_repo()
        try:
            from synapse.core import init_synapse, run_index, get_db_path
            from synapse.index.store import IndexDB
            
            init_synapse(tmpdir)
            run_index(tmpdir)
            
            with IndexDB(get_db_path(tmpdir)) as db:
                results = db.search_symbols("Greeter")
            
            assert len(results) > 0
            assert results[0]["kind"] == "class"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_search_finds_method(self):
        tmpdir = _create_temp_git_repo()
        try:
            from synapse.core import init_synapse, run_index, get_db_path
            from synapse.index.store import IndexDB
            
            init_synapse(tmpdir)
            run_index(tmpdir)
            
            with IndexDB(get_db_path(tmpdir)) as db:
                results = db.search_symbols("say_hello")
            
            assert len(results) > 0
            assert results[0]["kind"] == "method"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_full_cli_workflow(self):
        """Test the full init -> index -> status -> search workflow via CLI."""
        tmpdir = _create_temp_git_repo()
        try:
            # init
            result = _run_synapse(["init"], cwd=tmpdir)
            assert result.returncode == 0, f"init failed: {result.stderr}"
            
            # index
            result = _run_synapse(["index"], cwd=tmpdir)
            assert result.returncode == 0, f"index failed: {result.stderr}"
            
            # status
            result = _run_synapse(["status"], cwd=tmpdir)
            assert result.returncode == 0, f"status failed: {result.stderr}"
            
            # search
            result = _run_synapse(["search", "greet"], cwd=tmpdir)
            assert result.returncode == 0, f"search failed: {result.stderr}"
            assert "greet" in result.stdout.lower()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_status_shows_correct_info(self):
        tmpdir = _create_temp_git_repo()
        try:
            from synapse.core import init_synapse, run_index, get_status
            
            init_synapse(tmpdir)
            run_index(tmpdir)
            status = get_status(tmpdir)
            
            assert status["initialized"]
            assert status["files_indexed"] > 0
            assert status["symbols_indexed"] > 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestHelpCommand:
    """Test that --help works."""
    
    def test_synapse_help(self):
        result = subprocess.run(
            ["python", "-m", "synapse.cli", "--help"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "synapse" in result.stdout.lower()
