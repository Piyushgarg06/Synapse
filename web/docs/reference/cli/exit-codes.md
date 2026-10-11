---
title: Exit Codes
description: Complete listing of Synapse CLI exit codes and error conditions
---

# Exit Codes

Synapse adheres to standard UNIX process exit codes. Scripts and CI workflows can rely on these codes to detect errors.

---

## Exit Code Reference Table

| Exit Code | Classification | Meaning | Trigger Conditions |
|---|---|---|---|
| `0` | Success | Command completed successfully | Normal execution; search with 0 results; inspect on non-existent symbol |
| `1` | Operational Error | Command failed due to environment or data error | Outside Git repository; database corrupt; uninitialized repository; unwritable destination path; transaction rollback |
| `2` | Syntax / Usage Error | Invalid command line invocation | Invoked with no command; unknown subcommand; unknown flag; missing required argument |

---

## Detailed Trigger Conditions

### Exit Code 0: Success
- `synapse init` creates or verifies the database.
- `synapse index` completes indexing or exits with no-op.
- `synapse search` runs and prints results (even if 0 matches were found).
- `synapse inspect` reports symbol details or candidate options.

### Exit Code 1: Operational Error
- **Not a Git repository**: `find_repo_root()` raises `GitError`.
- **Uninitialized index**: Running `status`, `search`, `inspect`, `context`, or `export` before `init`.
- **Corrupt database**: SQLite raises unreadable header or disk corruption exception.
- **Write failure**: Destination file specified by `-o` cannot be created.

### Exit Code 2: Usage / Syntax Error
- Triggered directly by Python's `argparse` module:
  ```bash
  $ synapse unknown_cmd
  synapse: error: argument command: invalid choice: 'unknown_cmd'
  ```

---

## Shell Scripting Example

In Bash:
```bash
synapse index
status=$?
if [ $status -ne 0 ]; then
  echo "Indexing failed with exit code $status"
  exit 1
fi
```

In PowerShell:
```powershell
synapse index
if ($LASTEXITCODE -ne 0) {
  Write-Error "Indexing failed with code $LASTEXITCODE"
  exit 1
}
```
