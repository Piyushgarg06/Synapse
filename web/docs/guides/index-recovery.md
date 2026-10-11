---
title: Index Recovery
description: How to recover a broken or desynchronized index using rebuild or clean reset
---

# Index Recovery

Goal: Restore index consistency when the database is out of sync or the SQLite file is corrupted.

---

## Recovery Method 1: Full Rebuild

If the index state becomes desynchronized after git rebases or branch resets, force a clean rescan without deleting configuration:

```bash
synapse index --rebuild
```

Output:

```
Indexed 6 files, 11 symbols.
  Files processed: 6
  Symbols found: 11
```

### What this does
- Drops all records from `files`, `symbols`, `imports`, `inheritance`, `calls`, `references_`, and `edges`.
- Rescans all eligible tracked files at the current `HEAD` commit.
- Recalculates the complete knowledge graph and advances the checkpoint.

---

## Recovery Method 2: Corrupt Database Reset

If the `.synapse/index.db` file is truncated, damaged by a system crash, or unreadable:

### Step 1: Observe corruption message
When a corrupt database is opened, Synapse reports an operational error:

```bash
$ synapse init
Error: Synapse directory exists but database is corrupt: file is not a database
```

### Step 2: Remove the damaged database file
Delete `.synapse/index.db` from your repository root:

```bash
# On Linux / macOS
rm .synapse/index.db

# On Windows PowerShell
Remove-Item .synapse/index.db
```

### Step 3: Re-initialize and re-index
Run `init` to generate a fresh SQLite schema, followed by `index`:

```bash
synapse init
synapse index
```

Output:

```
Synapse initialized successfully (schema v1).
Indexed 6 files, 11 symbols.
  Files processed: 6
  Symbols found: 11
```

---

## How to Confirm It Worked

Run `synapse status` and verify that the database reports `Up to date: yes` with 0 unexpected parse errors:

```bash
synapse status
```

---

## Related Reference

- To understand transaction rollback safety, see [The Index and State](/concepts/the-index).
- For error message details, see [Error Messages](/reference/error-messages).
