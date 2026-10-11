---
title: synapse search
description: Reference documentation for the synapse search command
---

# synapse search

Searches symbols and files using tiered ranking over the persistent index.

---

## Synopsis

```
synapse search [-h] [--limit LIMIT] [--json] query
```

---

## Description

`synapse search` performs a search across indexed symbols (by name and qualified name) and tracked file paths. Results are ranked deterministically:
1. Exact match on symbol name.
2. Prefix match on symbol name.
3. Substring match on symbol name or qualified name.
4. Substring match on file path.

- **Reads**: `.synapse/index.db`.
- **Writes**: Nothing.
- **Never touches**: Source files or Git repository metadata.

---

## Options and Arguments

| Argument / Option | Type | Default | Description |
|---|---|---|---|
| `query` | Positional String | Required | Search term (symbol name, qualified name, or file path) |
| `--limit` | Integer | `20` | Maximum number of results to return |
| `--json` | Flag | `False` | Output search results as a JSON array |
| `-h`, `--help` | Flag | N/A | Show help message and exit |

---

## Output

### Human Format (Matches Found)
```
Found 2 result(s) for 'UserService':
  class     UserService  (backend/services/user_service.py:3)
  method    UserService.get_user  (backend/services/user_service.py:4)
```

### Human Format (No Matches)
```
No results found for 'nonexistent'.
```

### JSON Format (`--json`)
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
  },
  {
    "end_line": 5,
    "file_path": "backend/services/user_service.py",
    "id": "a12b4818e99259d0",
    "kind": "method",
    "name": "get_user",
    "qualified_name": "UserService.get_user",
    "start_line": 4
  }
]
```

---

## Exit Codes

| Code | Condition |
|---|---|
| `0` | Search completed (regardless of whether 0 or more matches were found) |
| `1` | Operational error (Synapse not initialized) |
| `2` | Missing required `query` argument or invalid option |

---

## Examples

### Example 1: Basic symbol search
```bash
$ synapse search UserService
Found 2 result(s) for 'UserService':
  class     UserService  (backend/services/user_service.py:3)
  method    UserService.get_user  (backend/services/user_service.py:4)
```

### Example 2: Bounded search with limit
```bash
$ synapse search Service --limit 1
Found 1 result(s) for 'Service':
  class     BaseService  (backend/base.py:1)
```
