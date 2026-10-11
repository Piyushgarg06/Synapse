---
title: The Index and State
description: Storage architecture, commit checkpoints, and working tree boundaries
---

# The Index and State

The index is a local SQLite database that maintains a structured representation of the repository at a specific Git commit checkpoint.

---

## Committed State Versus Working Tree

Synapse treats the Git commit tree at `HEAD` as the source of truth:

1. **Indexing reflects committed files**: Running `synapse index` reads and indexes the repository state at `HEAD`.
2. **Working tree changes are detected**: Synapse does not index uncommitted modifications until they are committed to Git.
3. **Dirty status is reported**: Running `synapse status` checks `git status --porcelain` (ignoring `.synapse/`) and warns if uncommitted modifications exist in your working tree.

Example status when working tree has uncommitted modifications:

```bash
$ synapse status
Synapse Status:
  HEAD commit:    cc17d9d8
  Last indexed:   cc17d9d8
  Up to date:     no (working tree dirty)
  Warning: Working tree has uncommitted changes not reflected in the index.
```

---

## The Checkpoint Mechanism

Every successful run of `synapse index` saves the current `HEAD` commit SHA to the `state` table:

```sql
SELECT value FROM state WHERE key = 'checkpoint';
```

When you invoke `synapse index` on subsequent runs:
- If `HEAD == checkpoint`, Synapse exits immediately with a no-op message:
  ```
  Repository unchanged since checkpoint cc17d9d8. Nothing to index.
  ```
- If `HEAD != checkpoint`, Synapse computes `git diff --name-status -M -z <checkpoint> HEAD` and updates only the changed files.

---

## Transactional Integrity

All write operations during an indexing pass occur inside a single SQLite transaction:

```python
cursor = db.conn.cursor()
try:
    for status, path, new_path in changes:
        # Update files, symbols, calls, imports
        ...
    build_graph_and_resolve(db, cursor=cursor)
    db.set_checkpoint(head, cursor=cursor)
    db.conn.commit()
except Exception as e:
    db.conn.rollback()
    return False, {"error": f"Incremental indexing failed: {e}"}
```

If an error or process termination occurs mid-run:
- Database modifications are rolled back.
- The `checkpoint` value is not updated.
- The next invocation retries the full set of pending changes safely.

---

## Storage Directory Layout

All internal state is kept within `.synapse/`:

```
.synapse/
  index.db         SQLite database file (WAL mode)
  index.db-wal     Write-Ahead Log (temporary)
  index.db-shm     Shared-memory index (temporary)
  .gitignore       Contains '*' to prevent accidental commits of index data
```

---

## Related Reference

- To force a full rebuild from scratch, see [index-recovery](/guides/index-recovery).
- For complete table column specifications, see [Storage Schema](/reference/storage-schema).
