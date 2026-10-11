"""Verify all synapse --help commands for GATE 9."""

import subprocess

cmds = ["", "init", "index", "status", "search", "inspect", "context", "export"]
for c in cmds:
    cmd_args = ["synapse"] + ([c] if c else []) + ["--help"]
    print(f"=== {' '.join(cmd_args)} ===")
    res = subprocess.run(cmd_args, capture_output=True, text=True)
    print(res.stdout.strip())
    print()
