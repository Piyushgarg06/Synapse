---
title: JSON Output Specifications
description: Field-by-field JSON specifications for all --json commands and exports
---

# JSON Output Specifications

This page documents the JSON shapes emitted by CLI commands when invoked with `--json` and by `synapse export json`.

---

## 1. `synapse status --json`

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

| Field | Type | Description |
|---|---|---|
| `initialized` | Boolean | `true` if `.synapse/index.db` exists and has a valid schema |
| `head_commit` | String | Short 8-character commit SHA at current `HEAD` |
| `checkpoint` | String | Short 8-character commit SHA of last successful index run |
| `up_to_date` | Boolean | `true` if `checkpoint == head` and working tree is clean |
| `dirty_working_tree` | Boolean | `true` if uncommitted modifications exist outside `.synapse/` |
| `files_indexed` | Integer | Total count of indexed source files |
| `symbols_indexed` | Integer | Total count of extracted symbols |
| `edges` | Integer | Total count of directed graph edges |
| `files_with_errors` | Integer | Total count of files with parse errors or size cap exceedance |

---

## 2. `synapse search --json`

Returns a list of matching symbol objects:

```json
[
  {
    "end_line": 12,
    "file_path": "backend/services/user_service.py",
    "id": "57992df372a7a124",
    "kind": "class",
    "name": "UserService",
    "qualified_name": "UserService",
    "start_line": 3
  }
]
```

---

## 3. `synapse inspect --json`

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
  "file_imports": [],
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

## 4. `synapse context --json`

```json
{
  "depth": 2,
  "disclaimer": "Note: This context document was generated deterministically...",
  "items": [
    {
      "callees": [],
      "callers": [],
      "end_line": 5,
      "file_path": "backend/services/user_service.py",
      "id": "a12b4818e99259d0",
      "is_stale": false,
      "kind": "method",
      "name": "get_user",
      "qualified_name": "UserService.get_user",
      "reason": "exact match",
      "snippet": "    def get_user(self, user_id: int):\n        return self.execute()\n",
      "start_line": 4,
      "truncated": false
    }
  ],
  "max_bytes": 8192,
  "max_results": 10,
  "query": "get_user",
  "results_count": 1,
  "unresolved_dependencies": []
}
```

---

## 5. `synapse export json`

```json
{
  "checkpoint": "acab20803451e04b4070e285a86a60346c4f74cf",
  "edges": [
    {
      "edge_type": "CALLS",
      "source_id": "a12b4818e99259d0",
      "target_id": "4bfc70378e3f43a9"
    }
  ],
  "edges_count": 27,
  "files": [],
  "files_count": 6,
  "references": [],
  "references_count": 15,
  "schema_version": 1,
  "symbols": [],
  "symbols_count": 11
}
```
