"""Tests for Phase 7: Hardening and Adversarial Audit.

GATE 7 requirements:
- Windows-style paths and CRLF source files.
- Unicode filenames and unicode source contents.
- Very large files exceeding size cap.
- Empty files.
- File changing / deleted between diff and read.
- Running from a repository subdirectory.
- Non-Git directory handling.
- Missing index handling.
- Corrupt database recovery.
- Confirm Synapse never modifies tracked source files.
- Confirm zero network / LLM calls.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import pytest

from synapse.core import init_synapse, run_index, get_status, get_db_path
from synapse.index.store import IndexDB
from synapse.git.ops import find_repo_root, GitError
from synapse.parsing.parser import MAX_FILE_SIZE


def _create_adversarial_repo() -> str:
    """Create a temporary git repository for hostile testing."""
    tmpdir = tempfile.mkdtemp(prefix="synapse_phase7_")
    subprocess.run(["git", "init", tmpdir], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.email", "test@test.com"], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.name", "Test"], capture_output=True, check=True)
    return tmpdir


class TestHardeningAndAdversarial:
    """Test adversarial scenarios and edge cases."""

    def test_crlf_line_endings_and_windows_paths(self):
        """CRLF line endings and Windows paths are correctly parsed and normalized."""
        repo = _create_adversarial_repo()
        try:
            # File with Windows CRLF
            crlf_content = "def crlf_func():\r\n    return 42\r\n"
            os.makedirs(os.path.join(repo, "subdir", "nested"), exist_ok=True)
            crlf_path = os.path.join(repo, "subdir", "nested", "crlf.py")
            with open(crlf_path, "wb") as f:
                f.write(crlf_content.encode("utf-8"))

            subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
            subprocess.run(["git", "-C", repo, "commit", "-m", "CRLF commit"], check=True)

            init_synapse(repo)
            ok, stats = run_index(repo)
            assert ok

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                syms = db.search_symbols("crlf_func")
                assert len(syms) == 1
                sym = syms[0]
                # Path stored with forward slashes on Windows
                assert sym["file_path"] == "subdir/nested/crlf.py"
                assert "\\" not in sym["file_path"]
                assert sym["start_line"] == 1
                assert sym["end_line"] == 2
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_unicode_filenames_and_source(self):
        """Unicode filenames and UTF-8 multi-byte characters are indexed accurately."""
        repo = _create_adversarial_repo()
        try:
            # Unicode filename
            unicode_file = os.path.join(repo, "données_测试.py")
            with open(unicode_file, "w", encoding="utf-8") as f:
                f.write("# 🚀 Unicode comment with emojis\ndef résumé_fonction():\n    return '日本語'\n")

            subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
            subprocess.run(["git", "-C", repo, "commit", "-m", "Unicode commit"], check=True)

            init_synapse(repo)
            ok, stats = run_index(repo)
            assert ok

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                syms = db.search_symbols("résumé_fonction")
                assert len(syms) == 1
                assert syms[0]["name"] == "résumé_fonction"
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_very_large_file_size_cap(self):
        """Files exceeding MAX_FILE_SIZE are recorded as parse errors without crashing."""
        repo = _create_adversarial_repo()
        try:
            large_file = os.path.join(repo, "huge.py")
            with open(large_file, "w") as f:
                f.write("def normal(): pass\n")

            subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
            subprocess.run(["git", "-C", repo, "commit", "-m", "Normal"], check=True)

            init_synapse(repo)

            # Test dispatcher directly with mocked file size exceeding cap
            from synapse.analysis.dispatcher import analyze_file
            import os as real_os
            orig_getsize = real_os.path.getsize

            def fake_getsize(path):
                if "huge.py" in path:
                    return MAX_FILE_SIZE + 1024
                return orig_getsize(path)

            real_os.path.getsize = fake_getsize
            try:
                analysis = analyze_file("huge.py", repo)
                assert analysis is not None
                assert analysis.parse_error is True
                assert "too large" in analysis.parse_error_message.lower()
            finally:
                real_os.path.getsize = orig_getsize
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_empty_file_handled_cleanly(self):
        """Zero-byte files are parsed cleanly without errors."""
        repo = _create_adversarial_repo()
        try:
            empty_file = os.path.join(repo, "empty.py")
            with open(empty_file, "w") as f:
                pass

            subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
            subprocess.run(["git", "-C", repo, "commit", "-m", "Empty file"], check=True)

            init_synapse(repo)
            ok, stats = run_index(repo)
            assert ok
            assert stats["files_processed"] == 1
            assert stats["symbols_found"] == 0

            db_path = get_db_path(repo)
            with IndexDB(db_path) as db:
                c = db.conn.cursor()
                c.execute("SELECT parse_error FROM files WHERE path = 'empty.py'")
                assert c.fetchone()[0] == 0
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_running_from_repo_subdirectory(self):
        """Synapse CLI commands work seamlessly when invoked from a repository subdirectory."""
        repo = _create_adversarial_repo()
        try:
            subdir = os.path.join(repo, "nested", "deep", "dir")
            os.makedirs(subdir, exist_ok=True)
            with open(os.path.join(repo, "root_file.py"), "w") as f:
                f.write("def root_fn(): return 'root'\n")

            subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
            subprocess.run(["git", "-C", repo, "commit", "-m", "Initial"], check=True)

            # Find repo root from deep subdirectory
            detected_root = find_repo_root(subdir)
            assert os.path.normpath(detected_root) == os.path.normpath(repo)

            # Run CLI from deep subdir
            res_init = subprocess.run(["python", "-m", "synapse.cli", "init"], cwd=subdir, capture_output=True, text=True)
            assert res_init.returncode == 0

            res_index = subprocess.run(["python", "-m", "synapse.cli", "index"], cwd=subdir, capture_output=True, text=True)
            assert res_index.returncode == 0

            res_search = subprocess.run(["python", "-m", "synapse.cli", "search", "root_fn"], cwd=subdir, capture_output=True, text=True)
            assert res_search.returncode == 0
            assert "root_fn" in res_search.stdout
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_non_git_directory_gives_clear_error(self):
        """Running synapse in a non-git directory exits non-zero with a clean message."""
        tmpdir = tempfile.mkdtemp()
        try:
            env = os.environ.copy()
            env["GIT_CEILING_DIRECTORIES"] = os.path.dirname(tmpdir)
            res = subprocess.run(
                ["python", "-m", "synapse.cli", "init"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                env=env,
            )
            assert res.returncode != 0
            assert "not a git repository" in res.stderr.lower() or "error" in res.stderr.lower()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_missing_index_gives_clear_error(self):
        """Running search/inspect before synapse init gives clean error message."""
        repo = _create_adversarial_repo()
        try:
            with open(os.path.join(repo, "test.py"), "w") as f:
                f.write("def f(): pass\n")
            subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
            subprocess.run(["git", "-C", repo, "commit", "-m", "init"], check=True)

            res = subprocess.run(
                ["python", "-m", "synapse.cli", "search", "f"],
                cwd=repo,
                capture_output=True,
                text=True,
            )
            assert res.returncode != 0
            assert "not initialized" in res.stderr.lower()
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_corrupt_database_recovery(self):
        """Corrupt database is detected and recovered through re-initialization or rebuild."""
        repo = _create_adversarial_repo()
        try:
            with open(os.path.join(repo, "app.py"), "w") as f:
                f.write("def app(): pass\n")
            subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
            subprocess.run(["git", "-C", repo, "commit", "-m", "commit"], check=True)

            init_synapse(repo)
            run_index(repo)

            # Corrupt database by writing arbitrary garbage bytes
            db_path = get_db_path(repo)
            with open(db_path, "wb") as f:
                f.write(b"CORRUPT_DATABASE_HEADER_GARBAGE")

            # Init detects corruption and reports it
            ok, msg = init_synapse(repo)
            assert ok is False
            assert "corrupt" in msg.lower()

            # Remove corrupt db file and re-init/index recovers cleanly
            os.remove(db_path)
            ok, msg = init_synapse(repo)
            assert ok is True
            ok_idx, stats = run_index(repo)
            assert ok_idx is True
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_tracked_source_files_never_modified_by_synapse(self):
        """Synapse never modifies or touches tracked user source files."""
        repo = _create_adversarial_repo()
        try:
            with open(os.path.join(repo, "critical_code.py"), "w") as f:
                f.write("def do_not_touch(): return 'pristine'\n")
            subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
            subprocess.run(["git", "-C", repo, "commit", "-m", "Original state"], check=True)

            # Run all synapse commands: init, index, search, inspect, context, export
            init_synapse(repo)
            run_index(repo)
            subprocess.run(["python", "-m", "synapse.cli", "search", "do_not_touch"], cwd=repo, check=True)
            subprocess.run(["python", "-m", "synapse.cli", "inspect", "do_not_touch"], cwd=repo, check=True)
            subprocess.run(["python", "-m", "synapse.cli", "context", "do_not_touch"], cwd=repo, check=True)
            subprocess.run(["python", "-m", "synapse.cli", "export", "json"], cwd=repo, check=True)

            # Verify git diff on tracked files is completely clean
            proc = subprocess.run(
                ["git", "-C", repo, "diff", "HEAD", "--", "critical_code.py"],
                capture_output=True,
                text=True,
                check=True,
            )
            assert proc.stdout.strip() == ""

            # Check status --porcelain shows no tracked modifications
            st = subprocess.run(
                ["git", "-C", repo, "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in st.stdout.splitlines():
                assert not line.endswith("critical_code.py")
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_no_network_or_llm_imports(self):
        """Audit confirms Synapse contains no network or LLM client calls."""
        import sys
        import synapse
        import synapse.core
        import synapse.cli
        import synapse.parsing.parser
        import synapse.analysis.dispatcher
        import synapse.index.store
        import synapse.graph.builder
        import synapse.retrieval.engine
        import synapse.export.exporter

        forbidden = ["openai", "anthropic", "google.generativeai", "langchain", "requests", "httpx", "urllib.request"]
        for mod in forbidden:
            assert mod not in sys.modules, f"Forbidden network/LLM module {mod} was imported!"
