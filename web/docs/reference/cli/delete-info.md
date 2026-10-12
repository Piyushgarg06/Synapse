---
title: synapse delete-info
description: Reference documentation for the synapse delete-info blast radius command
---

# synapse delete-info

Calculates and displays the blast-radius impact of deleting or modifying a file or symbol, identifying broken callers, affected subclasses, importers, and references.

---

## Synopsis

```
synapse delete-info [-h] [--json] target [symbol]
```

---

## Description

`synapse delete-info` queries `.synapse/index.db` to compute the full downstream impact before a file or function is modified or removed. It maps:

- **Importers**: Files that explicitly import the target file or symbol.
- **Callers**: Functions and methods across the codebase that call symbols defined in the target.
- **Subclasses**: Derived classes that inherit from classes defined in the target.
- **References**: Variable references and unresolved mentions targeting symbols in the file.

Properties:
- **Reads**: `.synapse/index.db`
- **Writes**: None (outputs to stdout)
- **Never touches**: Source files on disk, staging area, or Git commit history

---

## Options and Arguments

| Argument / Option | Type | Default | Description |
|---|---|---|---|
| `target` | Positional String | Required | Target file path or symbol name to analyze |
| `symbol` | Positional String | `None` | Specific symbol name within the file (optional) |
| `--json` | Flag | `False` | Output impact analysis as machine-readable JSON |
| `-h`, `--help` | Flag | N/A | Show help message and exit |

---

## Output

### File Deletion Impact

```
Blast Radius Analysis: backend/services/user_service.py
  Target: file (backend/services/user_service.py)
  Defined symbols: 3 (UserService, UserService.get_user, UserService.dynamic_call)
  Impacted files: 2

Broken Callers (external references):
  - handle_request -> UserService.get_user (backend/controllers/user_controller.py:18)

Affected Subclasses:
  - AdminUserService inherits UserService (backend/services/admin_service.py:8)

Files Importing Target:
  - backend/controllers/user_controller.py
  - backend/services/admin_service.py

Summary:
  Deleting backend/services/user_service.py will break 2 external file(s), 1 caller(s), and 1 subclass(es).
```

### Symbol Deletion Impact

```
Blast Radius Analysis: UserService.get_user
  Target: method (backend/services/user_service.py:4-5)
  Defined in: UserService
  Impacted files: 1

Direct Callers Broken:
  - handle_request (backend/controllers/user_controller.py:18)

Summary:
  Deleting UserService.get_user will break 1 caller(s) across 1 file(s).
```

### JSON Format (`--json`)

```json
{
  "target": "backend/services/user_service.py",
  "target_kind": "file",
  "defined_symbols_count": 3,
  "impacted_files_count": 2,
  "impacted_files": [
    "backend/controllers/user_controller.py",
    "backend/services/admin_service.py"
  ],
  "callers": [
    {
      "caller_file": "backend/controllers/user_controller.py",
      "caller_line": 18,
      "caller_name": "handle_request",
      "target_symbol": "UserService.get_user"
    }
  ],
  "subclasses": [
    {
      "child_class": "AdminUserService",
      "child_file": "backend/services/admin_service.py",
      "child_line": 8,
      "parent_class": "UserService"
    }
  ],
  "importers": [
    "backend/controllers/user_controller.py",
    "backend/services/admin_service.py"
  ]
}
```

---

## Exit Codes

| Code | Condition |
|---|---|
| `0` | Success (impact analysis computed and displayed) |
| `1` | Operational error (file or symbol not found in index) |
| `2` | Unknown command line option or syntax error |

---

## Examples

### Example 1 - Full File Impact

Check downstream effects before deleting a service module:

```bash
synapse delete-info backend/services/user_service.py
```

### Example 2 - Scoped Symbol Impact

Check which callers break if a specific method in a file is removed:

```bash
synapse delete-info backend/services/user_service.py get_user
```

### Example 3 - CI or Script Integration

Retrieve the impact analysis as JSON to assert zero broken callers in automated review scripts:

```bash
synapse delete-info backend/services/user_service.py --json
```
