"""Generate real clean-environment acceptance transcript for GATE 8."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import zipfile

repo = tempfile.mkdtemp(prefix="synapse_demo_")
os.environ["GIT_CEILING_DIRECTORIES"] = os.path.dirname(repo)

try:
    subprocess.run(["git", "init", repo], capture_output=True, check=True)
    subprocess.run(["git", "-C", repo, "config", "user.email", "demo@synapse.ai"], check=True)
    subprocess.run(["git", "-C", repo, "config", "user.name", "SynapseDemo"], check=True)

    os.makedirs(os.path.join(repo, "backend", "services"), exist_ok=True)
    with open(os.path.join(repo, "backend", "base.py"), "w", encoding="utf-8") as f:
        f.write(
            "class BaseService:\n"
            "    def __init__(self, name: str):\n"
            "        self.name = name\n"
            "    def execute(self):\n"
            "        return f'Running {self.name}'\n"
        )

    with open(os.path.join(repo, "backend", "services", "user_service.py"), "w", encoding="utf-8") as f:
        f.write(
            "from backend.base import BaseService\n\n"
            "class UserService(BaseService):\n"
            "    def get_user(self, user_id: int):\n"
            "        return self.execute()\n"
        )

    os.makedirs(os.path.join(repo, "frontend", "utils"), exist_ok=True)
    with open(os.path.join(repo, "frontend", "utils", "formatter.js"), "w", encoding="utf-8") as f:
        f.write(
            "export function formatName(user) {\n"
            "    return user.name.toUpperCase();\n"
            "}\n"
        )

    with open(os.path.join(repo, "frontend", "types.ts"), "w", encoding="utf-8") as f:
        f.write(
            "export interface User {\n"
            "    id: number;\n"
            "    name: string;\n"
            "}\n"
        )

    with open(os.path.join(repo, "frontend", "App.tsx"), "w", encoding="utf-8") as f:
        f.write(
            "import { User } from './types';\n"
            "import { formatName } from './utils/formatter';\n\n"
            "export function UserCard(props: { user: User }) {\n"
            "    return <div>{formatName(props.user)}</div>;\n"
            "}\n"
        )

    with open(os.path.join(repo, "syntax_err.py"), "w", encoding="utf-8") as f:
        f.write("def broken(:\n    pass\n")

    subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
    subprocess.run(["git", "-C", repo, "commit", "-m", "Initial commit with multi-language sample"], check=True)

    def run(cmd):
        cmd_str = " ".join(cmd)
        print(f"$ synapse {cmd_str}")
        res = subprocess.run(["synapse"] + cmd, cwd=repo, capture_output=True, text=True)
        if res.stdout:
            print(res.stdout.rstrip())
        if res.stderr:
            print(res.stderr.rstrip())
        print()

    run(["init"])
    run(["index"])
    run(["status"])
    run(["search", "UserService"])
    run(["inspect", "UserService"])
    run(["context", "get_user"])

    print("--- [Modifying repository: add auth_service, modify user_service, rename formatter, delete syntax_err] ---")
    with open(os.path.join(repo, "backend", "services", "auth_service.py"), "w", encoding="utf-8") as f:
        f.write(
            "from backend.base import BaseService\n\n"
            "class AuthService(BaseService):\n"
            "    def authenticate(self, token: str):\n"
            "        return True\n"
        )
    with open(os.path.join(repo, "backend", "services", "user_service.py"), "a", encoding="utf-8") as f:
        f.write("\n    def delete_user(self, user_id: int):\n        return True\n")
    os.remove(os.path.join(repo, "syntax_err.py"))
    os.rename(
        os.path.join(repo, "frontend", "utils", "formatter.js"),
        os.path.join(repo, "frontend", "utils", "string_formatter.js"),
    )
    with open(os.path.join(repo, "frontend", "App.tsx"), "r", encoding="utf-8") as f:
        c = f.read().replace("formatter", "string_formatter")
    with open(os.path.join(repo, "frontend", "App.tsx"), "w", encoding="utf-8") as f:
        f.write(c)

    subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
    subprocess.run(["git", "-C", repo, "commit", "-m", "Add auth, update user_service, rename formatter, delete syntax_err"], check=True)

    run(["index"])
    run(["status"])
    run(["export", "json", "-o", "synapse_export.json"])
    run(["export", "md", "-o", "synapse_export.md"])
    run(["export", "zip", "-o", "synapse_export.zip"])

    # Unpack zip
    print("$ unzip -l synapse_export.zip")
    with zipfile.ZipFile(os.path.join(repo, "synapse_export.zip")) as zf:
        for info in zf.infolist():
            print(f"  {info.filename:15s}  {info.file_size} bytes  (CRC: {info.CRC:08x})")

finally:
    shutil.rmtree(repo, ignore_errors=True)
