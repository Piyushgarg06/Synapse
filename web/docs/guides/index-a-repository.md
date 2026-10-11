---
title: Indexing a Repository
description: How to perform an initial structural index of a codebase
---

# Indexing a Repository

Goal: Initialize Synapse and generate a structural index of all supported files in a Git repository.

---

## Prerequisites

- Synapse installed (`synapse --help` exits 0).
- A Git repository containing at least one supported file (`.py`, `.js`, `.ts`, `.tsx`).

---

## Steps

### Step 1: Open the repository root
Change to your project directory:

```bash
cd /path/to/your/git/repo
```

### Step 2: Initialize Synapse tracking
Run `synapse init` to create `.synapse/` and configure the database schema:

```bash
synapse init
```

Output:

```
Synapse initialized successfully (schema v1).
```

### Step 3: Run the initial index
Execute `synapse index` to parse all tracked files:

```bash
synapse index
```

Output:

```
Indexed 6 files, 9 symbols.
  Files processed: 6
  Symbols found: 9
```

---

## How to Confirm It Worked

Run `synapse status` to verify that the index checkpoint matches your current `HEAD` commit:

```bash
synapse status
```

Output:

```
Synapse Status:
  HEAD commit:    cc17d9d8
  Last indexed:   cc17d9d8
  Up to date:     yes
  Files indexed:  6
  Symbols:        9
  Edges:          23
  Parse errors:   1
```

Confirm that `Up to date: yes` is displayed and that `Files indexed` matches your expected source file count.

---

## What Fails and How to Read Errors

### Running outside a Git repository
If you run `synapse init` in a directory not managed by Git:

```bash
$ synapse init
Error: Not in a git repository.
```

**Cause**: Git cannot find a `.git` directory in the current working directory or its parents.
**Fix**: Run `git init` or navigate to an existing Git repository.

---

## Related Guides

- To update the index after making commits, see [Keeping the Index Current](/guides/keep-the-index-current).
- To inspect extracted symbols, see [Inspecting Symbols](/guides/inspecting-symbols).
