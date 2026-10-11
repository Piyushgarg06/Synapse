---
title: Quickstart
description: A complete first session on a repository using Synapse
---

# Quickstart

This walkthrough takes you through initializing a repository, indexing source files, inspecting structural relationships, and exporting data.

---

## Step 1: Initialize Repository

Navigate to the root directory of any Git repository and run:

```bash
synapse init
```

Output:

```
Synapse initialized successfully (schema v1).
```

This creates the `.synapse/` directory and initializes `.synapse/index.db`. Re-running `synapse init` is safe and preserves existing index data:

```bash
$ synapse init
Synapse already initialized (schema v1). Existing data preserved.
```

---

## Step 2: Index the Codebase

Run the index command to scan tracked source files at the current `HEAD` commit:

```bash
synapse index
```

Output:

```
Indexed 6 files, 9 symbols.
  Files processed: 6
  Symbols found: 9
```

Synapse parses `.py`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, and `.tsx` files using Tree-sitter and stores definitions, calls, imports, and inheritance in SQLite.

---

## Step 3: Check Index Status

Verify index health and repository alignment:

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

The output confirms that the index matches `HEAD`. Files containing unparseable syntax are counted under `Parse errors` without aborting indexing.

---

## Step 4: Search for Symbols

Search for symbols by name or qualified name:

```bash
synapse search UserService
```

Output:

```
Found 2 result(s) for 'UserService':
  class     UserService  (backend/services/user_service.py:3)
  method    UserService.get_user  (backend/services/user_service.py:4)
```

---

## Step 5: Inspect Symbol Hierarchy

Inspect a specific symbol to view its location, base classes, and callers:

```bash
synapse inspect UserService
```

Output:

```
Symbol: UserService (class)
  File:     backend/services/user_service.py:3-12
  ID:       57992df372a7a124
  Inherits from:
    - BaseService (backend/base.py:1)
```

---

## Step 6: Generate Context for LLMs

Generate a bounded context document containing source snippets and immediate call relationships:

```bash
synapse context get_user
```

Output:

```
# Synapse Repository Context: get_user

Note: This context document was generated deterministically from static analysis. Snippets reflect indexed files. Dynamic calls, runtime reflection, and unindexed files remain unresolved and must not be assumed to be fully understood.

Found 1 item(s):

## Method: UserService.get_user
Path: `backend/services/user_service.py` (Lines 4-5)
Reason: exact match
```
    def get_user(self, user_id: int):
        return self.execute()
```
Calls:
  - BaseService.execute (backend/base.py:4)
```

---

## Step 7: Export the Index

Export the structural database into a standalone format:

```bash
synapse export json -o index.json
synapse export md -o index.md
synapse export zip -o snapshot.zip
```

Output:

```
Exported JSON index to index.json
Exported Markdown overview to index.md
Exported ZIP snapshot to snapshot.zip
```
