"""Execute and verify every single README command for GATE 9 checklist."""

import json
import os
import shutil
import subprocess
import tempfile

repo = tempfile.mkdtemp(prefix="synapse_readme_check_")
os.environ["GIT_CEILING_DIRECTORIES"] = os.path.dirname(repo)

try:
    subprocess.run(["git", "init", repo], capture_output=True, check=True)
    subprocess.run(["git", "-C", repo, "config", "user.email", "readme@synapse.test"], check=True)
    subprocess.run(["git", "-C", repo, "config", "user.name", "ReadmeTester"], check=True)

    with open(os.path.join(repo, "app.py"), "w", encoding="utf-8") as f:
        f.write(
            "class BaseService:\n"
            "    def execute(self): return 'base'\n\n"
            "class UserService(BaseService):\n"
            "    def get_user(self, uid):\n"
            "        return self.execute()\n"
        )
    subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
    subprocess.run(["git", "-C", repo, "commit", "-m", "Initial commit"], check=True)

    checklist = []

    def check(cmd_list, name):
        res = subprocess.run(["synapse"] + cmd_list, cwd=repo, capture_output=True, text=True)
        assert res.returncode == 0, f"Command failed: {' '.join(cmd_list)}\n{res.stderr}"
        checklist.append((name, f"synapse {' '.join(cmd_list)}", "PASS"))
        print(f"[VERIFIED] synapse {' '.join(cmd_list)} -> exit 0")

    check(["init"], "init")
    check(["index"], "index")
    check(["index", "--json"], "index --json")
    check(["index", "--rebuild"], "index --rebuild")
    check(["status"], "status")
    check(["status", "--json"], "status --json")
    check(["search", "UserService"], "search")
    check(["search", "--limit", "10", "UserService"], "search --limit")
    check(["search", "--json", "UserService"], "search --json")
    check(["inspect", "UserService"], "inspect")
    check(["inspect", "--depth", "2", "UserService"], "inspect --depth")
    check(["inspect", "--json", "UserService"], "inspect --json")
    check(["context", "get_user"], "context")
    check(["context", "--max-results", "5", "--max-bytes", "4096", "--depth", "2", "-o", "ctx.txt", "get_user"], "context with bounds and output")
    check(["context", "--json", "get_user"], "context --json")
    check(["export", "json", "-o", "out.json"], "export json")
    check(["export", "md", "-o", "out.md"], "export md")
    check(["export", "zip", "-o", "out.zip"], "export zip")

    print("\nALL README COMMANDS SUCCESSFULLY VERIFIED!")
finally:
    shutil.rmtree(repo, ignore_errors=True)
