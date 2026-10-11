---
title: Knowledge Graph
description: Node types, relationship edges, and structural guarantees
---

# Knowledge Graph

Synapse constructs a directed graph of your repository where code structures are nodes and verifiable static dependencies are edges.

---

## Node Types

The graph models code structure across six distinct node categories:

| Node Type | Description | Example Identifier |
|---|---|---|
| `Repository` | The root container representing the indexed Git repository | `repo:root` |
| `File` | A tracked source file in the repository | `file:backend/base.py` |
| `Module` | A logical module namespace derived from file paths | `module:backend.base` |
| `Class` | An object-oriented class declaration | `50877967954a0126` |
| `Function` | A top-level function declaration | `368ed7df7a37b677` |
| `Method` | A function declared within the scope of a class | `a12b4818e99259d0` |

---

## Relationship Edge Types

Relationships between nodes are represented by typed, directed edges:

### `CONTAINS`
Represents physical structural containment:
- `Repository` contains `File`.
- `File` contains `Class`, `Function`, or top-level declarations.
- `Class` contains `Method`.

### `DEFINES`
Represents the declaration relationship between an importable module and its exported symbols:
- `module:backend.base` defines `BaseService`.

### `IMPORTS`
Represents static module dependencies:
- `backend/services/user_service.py` imports `backend.base`.
- Records specific imported symbol names and aliases.

### `CALLS`
Represents an invocation of one callable entity by another:
- `UserService.get_user` calls `BaseService.execute`.
- Emitted only when the callee can be resolved to a known symbol.

### `INHERITS_FROM`
Represents class inheritance or interface implementation:
- `UserService` inherits from `BaseService`.
- TypeScript class implements an interface.

### `REFERENCES`
Represents lexical identifier usage within a symbol scope:
- Connects a symbol context to a referenced identifier name.

---

## Structural Guarantees

The graph enforces the following consistency guarantees:

1. **Uniqueness constraint**: The SQLite `edges` table enforces `UNIQUE(edge_type, source_id, target_id)`. Re-running indexing produces zero duplicate edges.
2. **Deterministic IDs**: Nodes use stable SHA-256 IDs based on file paths and scopes rather than database auto-increment keys.
3. **Stale record removal**: When a file is modified or deleted, all edges originating from or pointing to symbols within that file are removed before re-resolution.
4. **No runtime speculation**: A `CALLS` edge is never created if the target cannot be resolved statically.

---

## Related Reference

- To inspect graph neighbors, see [synapse inspect](/reference/cli/inspect).
- To view raw edge definitions in SQLite, see [Storage Schema](/reference/storage-schema).
