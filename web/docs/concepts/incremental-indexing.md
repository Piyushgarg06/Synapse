---
title: Incremental Indexing
description: How Synapse processes Git diffs, handles file changes, and maintains consistency
---

# Incremental Indexing

Synapse re-indexes only the files that changed between the previous successful checkpoint and the current `HEAD` commit.

---

## The Incremental Workflow

On every run after the initial index, Synapse executes the following sequence:

```
Last Checkpoint ─────────┐
                         ├──> git diff -M -z ──> Filter Exclusions ──> Re-parse Changed Files ──> Update Graph & Checkpoint
Current HEAD Commit ─────┘
```

1. **Read Checkpoint**: Fetches the last successfully processed commit SHA from the `state` table.
2. **Compute Diff**: Runs `git diff --name-status -M -z <checkpoint> HEAD` with rename detection enabled.
3. **Filter Paths**: Removes excluded paths (such as `node_modules`, test caches, or build outputs).
4. **Apply Changes**:
   - **Added (A)**: Parses the file, extracts symbols, and inserts records into SQLite.
   - **Modified (M)**: Deletes all old symbols, calls, imports, and references for the file, then re-parses the new contents.
   - **Deleted (D)**: Deletes all symbols, calls, imports, and references belonging to the removed file path.
   - **Renamed (R)**: Cleans records from the old path and parses the new path without leaving orphaned symbols.
5. **Re-resolve Graph**: Runs graph resolution to update cross-file callers and inheritance targets affected by the changed files.
6. **Advance Checkpoint**: Commits the transaction and updates `checkpoint` to the current `HEAD` SHA.

---

## Real Incremental Run Example

From our captured test repository, after adding `auth_service.py`, modifying `user_service.py`, deleting `syntax_error.py`, and renaming `formatter.js` to `string_formatter.js`:

```bash
$ synapse index
Incremental update: 5 files changed.
  Added: 1, Modified: 2, Deleted: 1, Renamed: 1
```

The output shows that only the 5 affected files were processed. Unchanged files were not re-parsed.

---

## Equivalence to Full Rebuild

A core design requirement of Synapse is that an incrementally updated index must be identical to a full fresh rebuild.

Our test suite enforces this with `test_equivalence_incremental_vs_full_rebuild`:
1. Repo A receives commits incrementally with additions, modifications, renames, and deletions.
2. Repo B is initialized from a clean clone of the final commit and runs a single full index.
3. The test extracts every row from `files`, `symbols`, and `edges` from both databases and asserts that they match row-for-row.

---

## Failure Safety and Rollback

If an error occurs while re-parsing an added or modified file:
- The active SQLite transaction rolls back.
- No partial records are committed.
- The `checkpoint` value remains at the previous commit SHA.
- On the next run, Synapse retries the full diff against the unchanged checkpoint.

---

## Related Reference

- To inspect the current checkpoint, see [synapse status](/reference/cli/status).
- To force a full index pass, see [synapse index --rebuild](/reference/cli/).
