---
title: Inspecting Symbols
description: How to inspect symbol definitions, callers, callees, and resolve ambiguity
---

# Inspecting Symbols

Goal: Inspect a symbol to examine its declaration location, inheritance tree, callers, callees, and unresolved references.

---

## Prerequisites

- An initialized and indexed repository (`synapse status` shows `Up to date: yes`).

---

## Steps

### Step 1: Search for the symbol
If you do not know the exact qualified name, search for candidates:

```bash
synapse search UserService
```

Output:

```
Found 2 result(s) for 'UserService':
  class     UserService  (backend/services/user_service.py:3)
  method    UserService.get_user  (backend/services/user_service.py:4)
```

### Step 2: Inspect the symbol definition
Inspect the symbol using its name:

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

The output confirms that `UserService` is defined at lines 3-12 and extends `BaseService`.

### Step 3: Traverse multi-hop callers and callees
To inspect callers and callees beyond the immediate 1-hop neighborhood, specify `--depth`:

```bash
synapse inspect UserService --depth 2
```

Increasing the depth traverses transitive callers up to the requested hop limit.

### Step 4: Resolve an ambiguous symbol name
If multiple files define a symbol with the same name, `synapse inspect` presents candidate matches:

```bash
$ synapse inspect calculate_hash
Ambiguous symbol query 'calculate_hash'. Multiple symbols match:
  - calculate_hash (method) in backend/base.py:7
  - calculate_hash (function) in frontend/utils/string_formatter.js:5
Specify the fully qualified name or refine query.
```

To inspect a specific candidate, re-run with its fully qualified name:

```bash
synapse inspect BaseService.calculate_hash
```

---

## How to Confirm It Worked

Check that the output includes the expected source file path, line bounds, and callers/callees for your target symbol.

---

## What Fails and How to Read Errors

### Symbol does not exist
If you query a symbol name not present in the index:

```bash
$ synapse inspect NonExistentClass
Symbol 'NonExistentClass' not found.
```

**Cause**: The symbol is not defined in any indexed file, or the file was excluded by pattern filters.
**Fix**: Verify the spelling using `synapse search` or check if the file extension is supported.

---

## Related Guides

- To generate LLM-ready snippets around this symbol, see [Generating Context for LLMs](/guides/context-generation).
- For complete flag documentation, see [synapse inspect Reference](/reference/cli/inspect).
