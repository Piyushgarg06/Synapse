---
title: Keeping the Index Current
description: How to perform incremental index updates after committing code
---

# Keeping the Index Current

Goal: Update the structural index incrementally as your codebase changes.

---

## Prerequisites

- An initialized repository with an existing index checkpoint (`synapse status` exits 0).
- Git commits adding, modifying, deleting, or renaming source files.

---

## Steps

### Step 1: Commit your changes
Ensure code modifications are committed to Git:

```bash
git add -A
git commit -m "Update user service and add auth service"
```

### Step 2: Check current status
Check the index status before updating:

```bash
synapse status
```

Output:

```
Synapse Status:
  HEAD commit:    acab2080
  Last indexed:   cc17d9d8
  Up to date:     no
  Warning: Index is behind HEAD. Run 'synapse index' to update.
```

The warning indicates that `HEAD` has advanced beyond the indexed checkpoint.

### Step 3: Run incremental index
Execute `synapse index` to process only changed files:

```bash
synapse index
```

Output:

```
Incremental update: 5 files changed.
  Added: 1, Modified: 2, Deleted: 1, Renamed: 1
```

Synapse re-parses only the modified files, removes deleted records, and updates cross-file links.

---

## How to Confirm It Worked

Re-run `synapse status`:

```bash
synapse status
```

Output:

```
Synapse Status:
  HEAD commit:    acab2080
  Last indexed:   acab2080
  Up to date:     yes
  Files indexed:  6
  Symbols:        11
  Edges:          27
```

Confirm that `Last indexed` matches `HEAD commit` and that `Up to date: yes` is displayed.

---

## What Fails and How to Read Errors

### Uncommitted changes in working tree
If you modify files on disk without committing them before indexing:

```bash
$ synapse status
Synapse Status:
  HEAD commit:    acab2080
  Last indexed:   acab2080
  Up to date:     no (working tree dirty)
  Warning: Working tree has uncommitted changes not reflected in the index.
```

**Cause**: Synapse indexes the commit tree at `HEAD`, not the uncommitted working directory.
**Fix**: Commit your working directory changes with `git commit` before running `synapse index`.

---

## Related Guides

- To understand how diffs are processed, see [Incremental Indexing](/concepts/incremental-indexing).
- To force a full re-scan if state becomes inconsistent, see [Index Recovery](/guides/index-recovery).
