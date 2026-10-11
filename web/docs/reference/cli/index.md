---
title: synapse index
description: Reference documentation for the synapse index command
---

# synapse index

Indexes the repository, updating structural symbols, relationships, and the commit checkpoint.

---

## Synopsis

```
synapse index [-h] [--rebuild] [--json]
```

---

## Description

`synapse index` parses eligible source files with Tree-sitter and updates the SQLite database. On the first run, it processes all tracked files at `HEAD`. On subsequent runs, it uses `git diff --name-status -M -z` to update only changed, added, deleted, or renamed files.

- **Reads**: Git tree and diffs; tracked source files on disk; `.synapse/index.db`.
- **Writes**: Records in `.synapse/index.db`; updates `checkpoint` in the `state` table.
- **Never touches**: User source files or Git commit history.

---

## Options

| Option | Type | Default | Description |
|---|---|---|---|
| `--rebuild` | Flag | `False` | Force a full rebuild of the index, discarding previous checkpoints |
| `--json` | Flag | `False` | Output indexing statistics as JSON |
| `-h`, `--help` | Flag | N/A | Show help message and exit |

---

## Output

### Human Format (Initial Run)
```
Indexed 6 files, 9 symbols.
  Files processed: 6
  Symbols found: 9
```

### Human Format (Incremental Run)
```
Incremental update: 5 files changed.
  Added: 1, Modified: 2, Deleted: 1, Renamed: 1
```

### Human Format (Unchanged Repository)
```
Repository unchanged since checkpoint cc17d9d8. Nothing to index.
```

### JSON Format (`--json`)
```json
{
  "checkpoint": "3a905fecbc10457a8721eec33e534606abfb33c6",
  "files_added": 0,
  "files_deleted": 0,
  "files_modified": 1,
  "files_renamed": 0,
  "files_skipped": 0,
  "message": "Incremental update: 1 files changed.",
  "mode": "incremental",
  "reparsed": 1,
  "symbols_found": 1
}
```

#### JSON Fields
- `mode`: String indicating `"full"` or `"incremental"`.
- `checkpoint`: The Git commit SHA saved as the new index checkpoint.
- `files_added`: Count of newly created source files indexed.
- `files_modified`: Count of existing source files re-indexed.
- `files_deleted`: Count of removed source files whose records were purged.
- `files_renamed`: Count of renamed source files updated.
- `symbols_found`: Total symbol declarations extracted in this pass.
- `reparsed`: Count of files parsed with Tree-sitter.

---

## Exit Codes

| Code | Condition |
|---|---|
| `0` | Indexing completed successfully (or no-op when unchanged) |
| `1` | Operational error (Synapse not initialized, or transaction rolled back on error) |
| `2` | Unknown option specified |

---

## Examples

### Example 1: Incremental update
```bash
$ synapse index
Incremental update: 5 files changed.
  Added: 1, Modified: 2, Deleted: 1, Renamed: 1
```

### Example 2: Forcing a full rebuild
```bash
$ synapse index --rebuild
Indexed 6 files, 11 symbols.
  Files processed: 6
  Symbols found: 11
```
