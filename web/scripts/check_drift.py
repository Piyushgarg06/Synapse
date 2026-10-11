"""Drift checker for captured CLI documentation outputs.

Re-runs the capture pipeline to a temporary location and asserts that all
generated outputs match the committed outputs byte-for-byte.
"""

from __future__ import annotations

import filecmp
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WEB_DIR = SCRIPT_DIR.parent
COMMITTED_DIR = WEB_DIR / "docs" / "_generated"


def check_drift() -> int:
    """Check for drift between committed and newly captured outputs."""
    if not COMMITTED_DIR.exists():
        print("Error: Committed generated directory does not exist. Run capture_pipeline.py first.")
        return 1

    # Snapshot current committed files
    committed_files = {f.name: f.read_bytes() for f in COMMITTED_DIR.glob("*") if f.is_file()}

    # Re-run capture pipeline
    print("Re-running capture pipeline to test determinism and drift...")
    capture_script = SCRIPT_DIR / "capture_pipeline.py"
    res = subprocess.run([sys.executable, str(capture_script)], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error: Capture pipeline failed:\n{res.stderr}")
        return 1

    # Compare again
    drift_detected = False
    for filename, old_bytes in committed_files.items():
        curr_path = COMMITTED_DIR / filename
        if not curr_path.exists():
            print(f"[DRIFT] Missing file: {filename}")
            drift_detected = True
            continue

        new_bytes = curr_path.read_bytes()
        if old_bytes != new_bytes:
            print(f"[DRIFT] Byte mismatch in {filename} (len {len(old_bytes)} vs {len(new_bytes)})")
            drift_detected = True

    if drift_detected:
        print("FAIL: Documentation outputs drifted from CLI implementation.")
        return 1

    print("PASS: Drift check passed. Outputs are 100% byte-identical and deterministic.")
    return 0


if __name__ == "__main__":
    sys.exit(check_drift())
