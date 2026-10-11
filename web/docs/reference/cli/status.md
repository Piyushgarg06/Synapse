---
title: synapse status
description: Reference documentation for the synapse status command
---

# synapse status

Displays the current index health, checkpoint alignment, and working tree cleanliness.

---

## Synopsis

```
synapse status [-h] [--json]
```

---

## Description

`synapse status` queries `.synapse/index.db` and the local Git working tree to report index metrics and verify whether uncommitted edits exist.

- **Reads**: `.synapse/index.db`, Git `HEAD`, and `git status --porcelain`.
- **Writes**: Nothing.
- **Never touches**: Source files or index records.

---

## Options

| Option | Type | Default | Description |
|---|---|---|---|
| `--json` | Flag | `False` | Output status as JSON |
| `-h`, `--help` | Flag | N/A | Show help message and exit |

---

## Output

### Human Format (Clean Working Tree)
```
Synapse Status:
  HEAD commit:    acab2080
  Last indexed:   acab2080
  Up to date:     yes
  Files indexed:  6
  Symbols:        11
  Edges:          27
```

### Human Format (Dirty Working Tree)
```
Synapse Status:
  HEAD commit:    acab2080
  Last indexed:   acab2080
  Up to date:     no (working tree dirty)
  Warning: Working tree has uncommitted changes not reflected in the index.
```

### JSON Format (`--json`)
```json
{
  "checkpoint": "acab2080",
  "dirty_working_tree": false,
  "edges": 27,
  "files_indexed": 6,
  "files_with_errors": 0,
  "head_commit": "acab2080",
  "initialized": true,
  "symbols_indexed": 11,
  "up_to_date": true
}
```

#### JSON Fields
- `initialized`: Boolean indicating whether Synapse has been initialized.
- `head_commit`: The short commit SHA at `HEAD`.
- `checkpoint`: The short commit SHA of the last successful index run.
- `up_to_date`: Boolean indicating whether `checkpoint == head` and the working tree is clean.
- `dirty_working_tree`: Boolean indicating whether uncommitted modifications exist outside `.synapse/`.
- `files_indexed`: Total source files currently stored in the database.
- `symbols_indexed`: Total symbol declarations extracted.
- `edges`: Total directed relationship edges in the knowledge graph.
- `files_with_errors`: Count of files with syntax errors or size cap exceedances.

---

## Exit Codes

| Code | Condition |
|---|---|
| `0` | Status successfully retrieved |
| `1` | Operational error (Synapse not initialized) |
| `2` | Unknown option specified |

---

## Examples

### Example 1: Standard status check
```bash
$ synapse status
Synapse Status:
  HEAD commit:    acab2080
  Last indexed:   acab2080
  Up to date:     yes
  Files indexed:  6
  Symbols:        11
  Edges:          27
```

### Example 2: Status with JSON output
```bash
$ synapse status --json
{
  "checkpoint": "acab2080",
  "dirty_working_tree": false,
  "edges": 27,
  "files_indexed": 6,
  "files_with_errors": 0,
  "head_commit": "acab2080",
  "initialized": true,
  "symbols_indexed": 11,
  "up_to_date": true
}
```
