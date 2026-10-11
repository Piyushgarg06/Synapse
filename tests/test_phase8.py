"""Tests for Phase 8: Clean-Environment Acceptance and End-to-End Workflow.

GATE 8 requirements:
- Multi-language sample repo (Python + JS + TS + TSX).
- Cross-file imports and class hierarchies.
- Syntax error handling without aborting.
- Full sequence: init -> index -> status -> search -> inspect -> context.
- Repository modifications: add, modify, delete, rename.
- Incremental indexing after commit -> status -> export (json, md, zip).
- ZIP archive unpacking and validation.
- Equivalence test: incremental index DB state exactly matches a full fresh rebuild.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import zipfile
import pytest

from synapse.index.store import IndexDB
from synapse.core import get_db_path, run_index


def _create_clean_acceptance_repo() -> str:
    """Create a temporary git repository with Python, JS, TS, TSX, and cross-file imports."""
    tmpdir = tempfile.mkdtemp(prefix="synapse_phase8_repo_")
    subprocess.run(["git", "init", tmpdir], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.email", "acceptance@synapse.test"], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.name", "AcceptanceRunner"], capture_output=True, check=True)

    # 1. Python files with class hierarchy and imports
    os.makedirs(os.path.join(tmpdir, "backend", "services"), exist_ok=True)
    with open(os.path.join(tmpdir, "backend", "base.py"), "w", encoding="utf-8") as f:
        f.write(
            "class BaseService:\n"
            "    def __init__(self, name: str):\n"
            "        self.name = name\n"
            "    def execute(self):\n"
            "        return f'Service {self.name}'\n"
        )

    with open(os.path.join(tmpdir, "backend", "services", "user_service.py"), "w", encoding="utf-8") as f:
        f.write(
            "from backend.base import BaseService\n\n"
            "class UserService(BaseService):\n"
            "    def get_user(self, user_id: int):\n"
            "        res = self.execute()\n"
            "        return {'id': user_id, 'service': res}\n"
        )

    # 2. JavaScript file
    os.makedirs(os.path.join(tmpdir, "frontend", "utils"), exist_ok=True)
    with open(os.path.join(tmpdir, "frontend", "utils", "formatter.js"), "w", encoding="utf-8") as f:
        f.write(
            "export function formatCurrency(amount) {\n"
            "    return '$' + amount.toFixed(2);\n"
            "}\n\n"
            "export class DataFormatter {\n"
            "    format(value) {\n"
            "        return formatCurrency(value);\n"
            "    }\n"
            "}\n"
        )

    # 3. TypeScript and TSX files
    with open(os.path.join(tmpdir, "frontend", "types.ts"), "w", encoding="utf-8") as f:
        f.write(
            "export interface UserProfile {\n"
            "    id: number;\n"
            "    name: string;\n"
            "}\n\n"
            "export class ProfileManager {\n"
            "    private profile: UserProfile;\n"
            "    constructor(p: UserProfile) {\n"
            "        this.profile = p;\n"
            "    }\n"
            "    getProfile(): UserProfile {\n"
            "        return this.profile;\n"
            "    }\n"
            "}\n"
        )

    with open(os.path.join(tmpdir, "frontend", "App.tsx"), "w", encoding="utf-8") as f:
        f.write(
            "import { ProfileManager } from './types';\n"
            "import { formatCurrency } from './utils/formatter';\n\n"
            "export function AppView(props: { manager: ProfileManager }) {\n"
            "    const p = props.manager.getProfile();\n"
            "    const salary = formatCurrency(1000);\n"
            "    return <div className=\"app\">{p.name} - {salary}</div>;\n"
            "}\n"
        )

    # 4. Syntax-error file (unclosed bracket)
    with open(os.path.join(tmpdir, "broken.py"), "w", encoding="utf-8") as f:
        f.write("def broken_syntax(:\n    return False\n")

    # Initial commit
    subprocess.run(["git", "-C", tmpdir, "add", "-A"], check=True)
    subprocess.run(["git", "-C", tmpdir, "commit", "-m", "Initial commit with multi-language sample"], check=True)
    return tmpdir


class TestPhase8CleanAcceptance:
    """Test full Phase 8 acceptance workflow."""

    def test_full_acceptance_workflow_and_equivalence(self):
        repo = _create_clean_acceptance_repo()
        try:
            # Step 1: synapse init
            res_init = subprocess.run(["synapse", "init"], cwd=repo, capture_output=True, text=True, check=True)
            assert "initialized" in res_init.stdout.lower()

            # Step 2: synapse index
            res_index = subprocess.run(["synapse", "index"], cwd=repo, capture_output=True, text=True, check=True)
            assert "indexed" in res_index.stdout.lower()

            # Step 3: synapse status
            res_status = subprocess.run(["synapse", "status", "--json"], cwd=repo, capture_output=True, text=True, check=True)
            status_data = json.loads(res_status.stdout)
            assert status_data["initialized"] is True
            assert status_data["files_indexed"] >= 5
            assert status_data["symbols_indexed"] > 0
            assert status_data["dirty_working_tree"] is False
            assert status_data["files_with_errors"] == 1  # broken.py

            # Step 4: synapse search
            res_search = subprocess.run(["synapse", "search", "UserService", "--json"], cwd=repo, capture_output=True, text=True, check=True)
            search_data = json.loads(res_search.stdout)
            assert isinstance(search_data, list)
            assert len(search_data) >= 1
            assert any(s["name"] == "UserService" for s in search_data)

            # Step 5: synapse inspect
            res_inspect = subprocess.run(["synapse", "inspect", "UserService", "--json"], cwd=repo, capture_output=True, text=True, check=True)
            inspect_data = json.loads(res_inspect.stdout)
            assert inspect_data["symbol"]["name"] == "UserService"
            assert any(b["name"] == "BaseService" for b in inspect_data["base_classes"])

            # Step 6: synapse context
            res_context = subprocess.run(["synapse", "context", "get_user", "--json"], cwd=repo, capture_output=True, text=True, check=True)
            ctx_data = json.loads(res_context.stdout)
            assert ctx_data["results_count"] >= 1
            assert any("get_user" in item["name"] for item in ctx_data["items"])
            assert any("def get_user" in item["snippet"] for item in ctx_data["items"])

            # Step 7: Modifications (modify, add, delete, rename)
            # Add file
            with open(os.path.join(repo, "backend", "services", "auth_service.py"), "w", encoding="utf-8") as f:
                f.write(
                    "from backend.base import BaseService\n\n"
                    "class AuthService(BaseService):\n"
                    "    def authenticate(self, token: str) -> bool:\n"
                    "        return token == 'valid'\n"
                )
            # Modify file
            with open(os.path.join(repo, "backend", "services", "user_service.py"), "a", encoding="utf-8") as f:
                f.write("\n    def delete_user(self, user_id: int):\n        return True\n")

            # Delete broken.py
            os.remove(os.path.join(repo, "broken.py"))

            # Rename frontend/utils/formatter.js -> frontend/utils/string_formatter.js
            old_js = os.path.join(repo, "frontend", "utils", "formatter.js")
            new_js = os.path.join(repo, "frontend", "utils", "string_formatter.js")
            os.rename(old_js, new_js)

            # Update import in App.tsx
            app_tsx = os.path.join(repo, "frontend", "App.tsx")
            with open(app_tsx, "r", encoding="utf-8") as f:
                app_content = f.read()
            with open(app_tsx, "w", encoding="utf-8") as f:
                f.write(app_content.replace("./utils/formatter", "./utils/string_formatter"))

            # Commit changes
            subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
            subprocess.run(["git", "-C", repo, "commit", "-m", "Feature additions, rename formatter, delete broken file"], check=True)

            # Step 8: Incremental synapse index
            res_inc_index = subprocess.run(["synapse", "index", "--json"], cwd=repo, capture_output=True, text=True, check=True)
            inc_stats = json.loads(res_inc_index.stdout)
            assert inc_stats["mode"] == "incremental"
            assert inc_stats["files_added"] >= 1
            assert inc_stats["files_modified"] >= 1
            assert inc_stats["files_deleted"] >= 1
            assert inc_stats["files_renamed"] >= 1

            # Step 9: synapse status after incremental
            res_status2 = subprocess.run(["synapse", "status", "--json"], cwd=repo, capture_output=True, text=True, check=True)
            status2_data = json.loads(res_status2.stdout)
            assert status2_data["files_with_errors"] == 0  # broken.py deleted
            assert status2_data["dirty_working_tree"] is False

            # Step 10: synapse exports
            export_dir = os.path.join(repo, "exports_out")
            os.makedirs(export_dir, exist_ok=True)
            json_file = os.path.join(export_dir, "export.json")
            md_file = os.path.join(export_dir, "export.md")
            zip_file = os.path.join(export_dir, "export.zip")

            subprocess.run(["synapse", "export", "json", "-o", json_file], cwd=repo, check=True)
            subprocess.run(["synapse", "export", "md", "-o", md_file], cwd=repo, check=True)
            subprocess.run(["synapse", "export", "zip", "-o", zip_file], cwd=repo, check=True)

            # Validate exports
            assert os.path.isfile(json_file)
            with open(json_file, "r", encoding="utf-8") as f:
                exported_json = json.load(f)
                assert exported_json["schema_version"] == 1
                assert "symbols" in exported_json
                assert "edges" in exported_json

            assert os.path.isfile(md_file)
            with open(md_file, "r", encoding="utf-8") as f:
                exported_md = f.read()
                assert "# Synapse Repository Index" in exported_md
                assert "AuthService" in exported_md

            assert os.path.isfile(zip_file)
            assert zipfile.is_zipfile(zip_file)
            with zipfile.ZipFile(zip_file, "r") as z:
                names = z.namelist()
                assert "index.json" in names
                assert "index.md" in names
                assert "README.txt" in names

            # Step 11: Equivalence test (incremental DB matches a fresh full rebuild)
            inc_db_path = get_db_path(repo)
            with IndexDB(inc_db_path) as db:
                c = db.conn.cursor()
                c.execute("SELECT path, language, parse_error FROM files ORDER BY path")
                inc_files = c.fetchall()
                c.execute("SELECT file_path, qualified_name, kind, start_line, end_line FROM symbols ORDER BY file_path, qualified_name, kind")
                inc_symbols = c.fetchall()
                c.execute("SELECT edge_type, source_id, target_id FROM edges ORDER BY edge_type, source_id, target_id")
                inc_edges = c.fetchall()

            # Fresh clone / rebuild to verify full index equivalence
            rebuild_repo = tempfile.mkdtemp(prefix="synapse_rebuild_")
            try:
                # Clone repository at the exact same commit
                subprocess.run(["git", "clone", repo, rebuild_repo], capture_output=True, check=True)
                subprocess.run(["synapse", "init"], cwd=rebuild_repo, check=True)
                subprocess.run(["synapse", "index"], cwd=rebuild_repo, check=True)

                rebuild_db_path = get_db_path(rebuild_repo)
                with IndexDB(rebuild_db_path) as db_rb:
                    c_rb = db_rb.conn.cursor()
                    c_rb.execute("SELECT path, language, parse_error FROM files ORDER BY path")
                    rb_files = c_rb.fetchall()
                    c_rb.execute("SELECT file_path, qualified_name, kind, start_line, end_line FROM symbols ORDER BY file_path, qualified_name, kind")
                    rb_symbols = c_rb.fetchall()
                    c_rb.execute("SELECT edge_type, source_id, target_id FROM edges ORDER BY edge_type, source_id, target_id")
                    rb_edges = c_rb.fetchall()

                # Compare files, symbols, and edges between incremental and full rebuild
                assert [tuple(r) for r in inc_files] == [tuple(r) for r in rb_files]
                assert [tuple(r) for r in inc_symbols] == [tuple(r) for r in rb_symbols]
                assert [tuple(r) for r in inc_edges] == [tuple(r) for r in rb_edges]
            finally:
                shutil.rmtree(rebuild_repo, ignore_errors=True)

        finally:
            shutil.rmtree(repo, ignore_errors=True)
