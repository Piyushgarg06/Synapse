"""Deterministic capture pipeline for Synapse documentation.

Creates a fixed multi-language sample repository, executes all documented
commands and edge cases, and writes deterministic, reproducible outputs
to web/docs/_generated/.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WEB_DIR = SCRIPT_DIR.parent
GENERATED_DIR = WEB_DIR / "docs" / "_generated"

# Fixed git author/committer environment for byte-identical commit hashes
GIT_ENV = os.environ.copy()
GIT_ENV["GIT_AUTHOR_NAME"] = "SynapseDemo"
GIT_ENV["GIT_COMMITTER_NAME"] = "SynapseDemo"
GIT_ENV["GIT_AUTHOR_EMAIL"] = "demo@synapse.ai"
GIT_ENV["GIT_COMMITTER_EMAIL"] = "demo@synapse.ai"
GIT_ENV["GIT_AUTHOR_DATE"] = "2026-01-01T00:00:00Z"
GIT_ENV["GIT_COMMITTER_DATE"] = "2026-01-01T00:00:00Z"


def clean_output(text: str, repo_dir: str) -> str:
    """Normalize absolute paths to deterministic relative paths."""
    # Normalize Windows and POSIX path separators
    text = text.replace(repo_dir, "/workspace/demo-repo")
    text = text.replace(repo_dir.replace("/", "\\"), "/workspace/demo-repo")
    text = text.replace(repo_dir.replace("\\", "/"), "/workspace/demo-repo")
    # Replace backslashes in paths with forward slashes for cross-platform determinism
    lines = []
    for line in text.splitlines():
        # Keep consistent line endings
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


def run_cmd(args: list[str], cwd: str, env: dict | None = None) -> tuple[int, str, str]:
    """Run command and return (exit_code, stdout, stderr)."""
    e = env or GIT_ENV
    res = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=e,
    )
    return res.returncode, res.stdout, res.stderr


def build_sample_repo(repo: str):
    """Create the initial deterministic sample repository."""
    e = GIT_ENV.copy()
    e["GIT_CEILING_DIRECTORIES"] = os.path.dirname(repo)

    run_cmd(["git", "init", repo], cwd=repo, env=e)
    run_cmd(["git", "-C", repo, "config", "user.email", "demo@synapse.ai"], cwd=repo, env=e)
    run_cmd(["git", "-C", repo, "config", "user.name", "SynapseDemo"], cwd=repo, env=e)

    # 1. Python base service
    os.makedirs(os.path.join(repo, "backend", "services"), exist_ok=True)
    with open(os.path.join(repo, "backend", "base.py"), "w", encoding="utf-8", newline="\n") as f:
        f.write(
            "class BaseService:\n"
            "    def __init__(self, name: str):\n"
            "        self.name = name\n\n"
            "    def execute(self):\n"
            "        return f'Running {self.name}'\n\n"
            "    def calculate_hash(self):\n"
            "        return hash(self.name)\n"
        )

    # 2. Python user service inheriting from base
    with open(os.path.join(repo, "backend", "services", "user_service.py"), "w", encoding="utf-8", newline="\n") as f:
        f.write(
            "from backend.base import BaseService\n\n"
            "class UserService(BaseService):\n"
            "    def get_user(self, user_id: int):\n"
            "        return self.execute()\n\n"
            "    def dynamic_call(self, handler, action: str):\n"
            "        # Dynamic invocation remains unresolved in static analysis\n"
            "        return getattr(handler, action)()\n"
        )

    # 3. JavaScript utility
    os.makedirs(os.path.join(repo, "frontend", "utils"), exist_ok=True)
    with open(os.path.join(repo, "frontend", "utils", "formatter.js"), "w", encoding="utf-8", newline="\n") as f:
        f.write(
            "export function formatName(user) {\n"
            "    return user.name.toUpperCase();\n"
            "}\n\n"
            "export function calculate_hash(data) {\n"
            "    return data.length;\n"
            "}\n"
        )

    # 4. TypeScript interfaces
    with open(os.path.join(repo, "frontend", "types.ts"), "w", encoding="utf-8", newline="\n") as f:
        f.write(
            "export interface User {\n"
            "    id: number;\n"
            "    name: string;\n"
            "}\n"
        )

    # 5. TSX component
    with open(os.path.join(repo, "frontend", "App.tsx"), "w", encoding="utf-8", newline="\n") as f:
        f.write(
            "import { User } from './types';\n"
            "import { formatName } from './utils/formatter';\n\n"
            "export function UserCard(props: { user: User }) {\n"
            "    return <div className=\"card\">{formatName(props.user)}</div>;\n"
            "}\n"
        )

    # 6. Syntax error file (unclosed parenthesis)
    with open(os.path.join(repo, "syntax_error.py"), "w", encoding="utf-8", newline="\n") as f:
        f.write("def broken_definition(:\n    pass\n")

    run_cmd(["git", "-C", repo, "add", "-A"], cwd=repo, env=e)
    run_cmd(["git", "-C", repo, "commit", "-m", "Initial commit with multi-language sample"], cwd=repo, env=e)


def main() -> int:
    """Run full capture pipeline and write outputs."""
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    tmp_base = tempfile.mkdtemp(prefix="synapse_capture_")
    repo = os.path.join(tmp_base, "sample_repo")
    os.makedirs(repo, exist_ok=True)

    non_git_dir = os.path.join(tmp_base, "not_a_repo")
    os.makedirs(non_git_dir, exist_ok=True)

    try:
        build_sample_repo(repo)
        e = GIT_ENV.copy()
        e["GIT_CEILING_DIRECTORIES"] = tmp_base

        captures = {}

        def record(scenario_id: str, command: list[str], cwd: str = repo, custom_env: dict | None = None):
            code, stdout, stderr = run_cmd(command, cwd=cwd, env=custom_env or e)
            clean_cmd = " ".join(command)
            clean_out = clean_output(stdout, repo)
            clean_err = clean_output(stderr, repo)

            data = {
                "scenario": scenario_id,
                "command": clean_cmd,
                "exit_code": code,
                "stdout": clean_out,
                "stderr": clean_err,
            }
            captures[scenario_id] = data

            # Write individual file
            out_file = GENERATED_DIR / f"{scenario_id}.txt"
            content = f"$ {clean_cmd}\n"
            if clean_out:
                content += clean_out + "\n"
            if clean_err:
                content += clean_err + "\n"
            out_file.write_text(content.strip() + "\n", encoding="utf-8")

        # 1. Non-git directory error
        record("01_non_git_directory", ["synapse", "init"], cwd=non_git_dir)

        # 2. Uninitialized repo error
        record("02_uninitialized_search", ["synapse", "search", "UserService"])

        # 3. synapse init
        record("03_init_initial", ["synapse", "init"])

        # 4. synapse init repeated (safe rerun)
        record("04_init_repeated", ["synapse", "init"])

        # 5. synapse index (initial full run)
        record("05_index_initial", ["synapse", "index"])

        # 6. synapse status (clean, 1 syntax error)
        record("06_status_initial", ["synapse", "status"])

        # 7. synapse status --json
        record("07_status_json", ["synapse", "status", "--json"])

        # 8. synapse search (single match)
        record("08_search_user_service", ["synapse", "search", "UserService"])

        # 9. synapse search (ambiguous symbol)
        record("09_search_calculate_hash", ["synapse", "search", "calculate_hash"])

        # 10. synapse search --json
        record("10_search_json", ["synapse", "search", "UserService", "--json"])

        # 11. synapse inspect (class with hierarchy)
        record("11_inspect_user_service", ["synapse", "inspect", "UserService"])

        # 12. synapse inspect (ambiguous query)
        record("12_inspect_ambiguous", ["synapse", "inspect", "calculate_hash"])

        # 13. synapse inspect --json
        record("13_inspect_json", ["synapse", "inspect", "UserService", "--json"])

        # 14. synapse context (exact match with snippet and calls)
        record("14_context_get_user", ["synapse", "context", "get_user"])

        # 15. synapse context with bounding flags
        record("15_context_bounded", ["synapse", "context", "get_user", "--max-results", "5", "--max-bytes", "4096", "--depth", "2"])

        # 16. synapse context --json
        record("16_context_json", ["synapse", "context", "get_user", "--json"])

        # 17. synapse index unchanged (no-op)
        record("17_index_noop", ["synapse", "index"])

        # 18. Dirty working tree test
        with open(os.path.join(repo, "backend", "base.py"), "a", encoding="utf-8", newline="\n") as f:
            f.write("\n# Uncommitted edit in working tree\n")
        record("18_status_dirty", ["synapse", "status"])

        # Revert uncommitted edit
        run_cmd(["git", "-C", repo, "checkout", "--", "backend/base.py"], cwd=repo, env=e)

        # 19. Commit modifications: add auth_service, modify user_service, rename formatter, delete syntax_error
        with open(os.path.join(repo, "backend", "services", "auth_service.py"), "w", encoding="utf-8", newline="\n") as f:
            f.write(
                "from backend.base import BaseService\n\n"
                "class AuthService(BaseService):\n"
                "    def authenticate(self, token: str) -> bool:\n"
                "        return token == 'valid'\n"
            )
        with open(os.path.join(repo, "backend", "services", "user_service.py"), "a", encoding="utf-8", newline="\n") as f:
            f.write("\n    def delete_user(self, user_id: int):\n        return True\n")

        os.remove(os.path.join(repo, "syntax_error.py"))
        os.rename(
            os.path.join(repo, "frontend", "utils", "formatter.js"),
            os.path.join(repo, "frontend", "utils", "string_formatter.js"),
        )
        app_tsx = os.path.join(repo, "frontend", "App.tsx")
        with open(app_tsx, "r", encoding="utf-8") as f:
            content = f.read().replace("formatter", "string_formatter")
        with open(app_tsx, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

        # Commit changes with fixed timestamp for determinism
        e2 = e.copy()
        e2["GIT_AUTHOR_DATE"] = "2026-01-02T00:00:00Z"
        e2["GIT_COMMITTER_DATE"] = "2026-01-02T00:00:00Z"
        run_cmd(["git", "-C", repo, "add", "-A"], cwd=repo, env=e2)
        run_cmd(["git", "-C", repo, "commit", "-m", "Add auth, modify user, rename formatter, delete syntax_error"], cwd=repo, env=e2)

        # 20. Incremental index
        record("20_index_incremental", ["synapse", "index"])

        # 21. Incremental index --json
        # Create another small commit to show JSON incremental update
        with open(os.path.join(repo, "backend", "services", "auth_service.py"), "a", encoding="utf-8", newline="\n") as f:
            f.write("\n    def logout(self): return True\n")
        e3 = e.copy()
        e3["GIT_AUTHOR_DATE"] = "2026-01-03T00:00:00Z"
        e3["GIT_COMMITTER_DATE"] = "2026-01-03T00:00:00Z"
        run_cmd(["git", "-C", repo, "add", "-A"], cwd=repo, env=e3)
        run_cmd(["git", "-C", repo, "commit", "-m", "Add logout method"], cwd=repo, env=e3)

        record("21_index_incremental_json", ["synapse", "index", "--json"])

        # 22. Status after incremental
        record("22_status_post_incremental", ["synapse", "status"])

        # 23. Full rebuild recovery
        record("23_index_rebuild", ["synapse", "index", "--rebuild"])

        # 24. Exports
        export_json_path = os.path.join(repo, "synapse_export.json")
        export_md_path = os.path.join(repo, "synapse_export.md")
        export_zip_path = os.path.join(repo, "synapse_export.zip")

        record("24_export_json", ["synapse", "export", "json", "-o", "synapse_export.json"])
        record("25_export_md", ["synapse", "export", "md", "-o", "synapse_export.md"])
        record("26_export_zip", ["synapse", "export", "zip", "-o", "synapse_export.zip"])

        # Save actual sample export.json for interactive graph component
        if os.path.isfile(export_json_path):
            with open(export_json_path, "r", encoding="utf-8") as f:
                sample_export = json.load(f)
            (GENERATED_DIR / "sample_export.json").write_text(
                json.dumps(sample_export, indent=2, sort_keys=True), encoding="utf-8"
            )

        # 27. CLI Help commands
        help_cmds = [
            ("27_help_main", ["synapse", "--help"]),
            ("28_help_init", ["synapse", "init", "--help"]),
            ("29_help_index", ["synapse", "index", "--help"]),
            ("30_help_status", ["synapse", "status", "--help"]),
            ("31_help_search", ["synapse", "search", "--help"]),
            ("32_help_inspect", ["synapse", "inspect", "--help"]),
            ("33_help_context", ["synapse", "context", "--help"]),
            ("34_help_export", ["synapse", "export", "--help"]),
        ]
        for s_id, cmd in help_cmds:
            record(s_id, cmd)

        # Write master manifest
        manifest_file = GENERATED_DIR / "manifest.json"
        manifest_file.write_text(json.dumps(captures, indent=2, sort_keys=True), encoding="utf-8")

        print(f"Capture pipeline completed: {len(captures)} scenarios captured to {GENERATED_DIR}.")
        return 0

    finally:
        shutil.rmtree(tmp_base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
