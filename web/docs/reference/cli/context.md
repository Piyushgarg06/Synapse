---
title: synapse context
description: Reference documentation for the synapse context command
---

# synapse context

Retrieves focused repository context documents with verified source snippets, call relationships, and unresolved dependencies.

---

## Synopsis

```
synapse context [-h] [--max-results MAX_RESULTS] [--max-bytes MAX_BYTES] [--depth DEPTH] [-o OUTPUT] [--json] query
```

---

## Description

`synapse context` extracts source snippets directly from files on disk for matched symbols, retrieves callers and callees up to `--depth` hops, and lists unresolved external dependencies.

- **Reads**: `.synapse/index.db`, source files on disk.
- **Writes**: Destination file specified by `-o` or `--output` (prints to stdout if omitted).
- **Never touches**: Git repository state.

---

## Options and Arguments

| Argument / Option | Type | Default | Description |
|---|---|---|---|
| `query` | Positional String | Required | Target symbol or identifier query |
| `--max-results` | Integer | `10` | Maximum number of context items to include |
| `--max-bytes` | Integer | `8192` | Maximum byte length per individual source snippet |
| `--depth` | Integer | `2` | Traversal depth for callers and callees |
| `-o`, `--output` | String | `None` | Output file path to write context to |
| `--json` | Flag | `False` | Output context document as JSON |
| `-h`, `--help` | Flag | N/A | Show help message and exit |

---

## Output

### Human Format (Standard Context)
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

### JSON Format (`--json`)
```json
{
  "depth": 2,
  "disclaimer": "Note: This context document was generated deterministically from static analysis...",
  "items": [
    {
      "callees": [
        {
          "file_path": "backend/base.py",
          "kind": "method",
          "name": "execute",
          "qualified_name": "BaseService.execute",
          "rel_id": "4bfc70378e3f43a9",
          "start_line": 4
        }
      ],
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

## Exit Codes

| Code | Condition |
|---|---|
| `0` | Context generated successfully |
| `1` | Operational error (Synapse not initialized, or destination path unwritable) |
| `2` | Missing required `query` argument or invalid option |

---

## Examples

### Example 1: Bounded context query
```bash
$ synapse context get_user --max-results 5 --max-bytes 4096 --depth 2
# Synapse Repository Context: get_user
Found 1 item(s):
...
```

### Example 2: Save context to a markdown file
```bash
$ synapse context get_user -o prompt_context.md
Context written to prompt_context.md
```
