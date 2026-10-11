---
title: synapse inspect
description: Reference documentation for the synapse inspect command
---

# synapse inspect

Inspects a symbol's definition, enclosing lexical scope, base classes, callers, callees, and unresolved references.

---

## Synopsis

```
synapse inspect [-h] [--depth DEPTH] [--json] symbol
```

---

## Description

`synapse inspect` retrieves detailed structural information for a specified symbol name or fully qualified name. It traverses graph relationships up to `--depth` hops to report base classes, subclasses, callers, and callees.

- **Reads**: `.synapse/index.db`.
- **Writes**: Nothing.
- **Never touches**: Source files or repository metadata.

---

## Options and Arguments

| Argument / Option | Type | Default | Description |
|---|---|---|---|
| `symbol` | Positional String | Required | Name or qualified name of the symbol to inspect |
| `--depth` | Integer | `1` | Traversal depth for relationship edges |
| `--json` | Flag | `False` | Output inspection data as JSON |
| `-h`, `--help` | Flag | N/A | Show help message and exit |

---

## Output

### Human Format (Single Match)
```
Symbol: UserService (class)
  File:     backend/services/user_service.py:3-12
  ID:       57992df372a7a124
  Inherits from:
    - BaseService (backend/base.py:1)
```

### Human Format (Ambiguous Match)
When a symbol query matches definitions in multiple files, Synapse prints candidate locations:

```
Ambiguous symbol query 'calculate_hash'. Multiple symbols match:
  - calculate_hash (method) in backend/base.py:7
  - calculate_hash (function) in frontend/utils/string_formatter.js:5
Specify the fully qualified name or refine query.
```

### JSON Format (`--json`)
```json
{
  "ambiguous": false,
  "base_classes": [
    {
      "file_path": "backend/base.py",
      "kind": "class",
      "name": "BaseService",
      "qualified_name": "BaseService",
      "rel_id": "50877967954a0126",
      "start_line": 1
    }
  ],
  "callees": [],
  "callers": [],
  "depth": 1,
  "file_imports": [
    {
      "alias": null,
      "imported_names": "BaseService",
      "module_name": "backend.base"
    }
  ],
  "found": true,
  "parent": null,
  "subclasses": [],
  "symbol": {
    "end_column": 0,
    "end_line": 12,
    "file_path": "backend/services/user_service.py",
    "id": "57992df372a7a124",
    "kind": "class",
    "name": "UserService",
    "ordinal": 0,
    "qualified_name": "UserService",
    "start_column": 0,
    "start_line": 3
  },
  "unresolved_references": []
}
```

---

## Exit Codes

| Code | Condition |
|---|---|
| `0` | Symbol inspected successfully (or ambiguous candidate list printed) |
| `1` | Operational error (Synapse not initialized) |
| `2` | Missing required `symbol` argument or invalid option |

---

## Examples

### Example 1: Inspect class hierarchy
```bash
$ synapse inspect UserService
Symbol: UserService (class)
  File:     backend/services/user_service.py:3-12
  ID:       57992df372a7a124
  Inherits from:
    - BaseService (backend/base.py:1)
```

### Example 2: Resolving an ambiguous symbol
```bash
$ synapse inspect BaseService.calculate_hash
Symbol: BaseService.calculate_hash (method)
  File:     backend/base.py:7-8
  ID:       584e5c34ca794587
```
