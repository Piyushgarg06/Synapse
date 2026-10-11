---
title: Storage Schema
description: Complete SQLite database schema specification for .synapse/index.db
---

# Storage Schema

Synapse stores all structural information in an embedded SQLite database at `.synapse/index.db`.

---

## Database Pragmas

Every database connection executes:
```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
```

---

## Schema Tables

### 1. `state`
Stores system configuration and commit checkpoints.

```sql
CREATE TABLE IF NOT EXISTS state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

- `schema_version`: Current schema version integer string (currently `"1"`).
- `checkpoint`: Full Git commit SHA of the last successful indexing run.

---

### 2. `files`
Tracks source files eligible for parsing.

```sql
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    language TEXT NOT NULL,
    has_errors INTEGER NOT NULL DEFAULT 0,
    parse_error INTEGER NOT NULL DEFAULT 0,
    parse_error_message TEXT NOT NULL DEFAULT ''
);
```

- `path`: Repo-relative path with forward slashes.
- `language`: Normalized language string (`python`, `javascript`, `typescript`, `tsx`).
- `has_errors`: 1 if Tree-sitter detected ERROR syntax nodes during traversal.
- `parse_error`: 1 if the file could not be parsed or exceeded the 10 MB size cap.

---

### 3. `symbols`
Stores declared classes, methods, functions, and interfaces.

```sql
CREATE TABLE IF NOT EXISTS symbols (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    qualified_name TEXT NOT NULL,
    kind TEXT NOT NULL,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    start_byte INTEGER NOT NULL,
    end_byte INTEGER NOT NULL,
    start_line INTEGER NOT NULL,
    start_column INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    end_column INTEGER NOT NULL,
    ordinal INTEGER NOT NULL DEFAULT 0,
    UNIQUE(file_path, qualified_name, kind, ordinal)
);
```

---

### 4. `imports`
Stores file-level import statements.

```sql
CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    module_name TEXT NOT NULL,
    imported_names TEXT NOT NULL DEFAULT '',
    alias TEXT,
    is_default INTEGER NOT NULL DEFAULT 0,
    is_namespace INTEGER NOT NULL DEFAULT 0,
    start_line INTEGER,
    end_line INTEGER
);
```

---

### 5. `inheritance`
Stores explicit class inheritance and interface implementation declarations.

```sql
CREATE TABLE IF NOT EXISTS inheritance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    class_name TEXT NOT NULL,
    base_class_name TEXT NOT NULL
);
```

---

### 6. `calls`
Stores static call sites detected within symbol scopes.

```sql
CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    caller_qualified_name TEXT NOT NULL,
    callee_name TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER
);
```

---

### 7. `references_`
Stores syntactic, resolved, and unresolved references.

```sql
CREATE TABLE IF NOT EXISTS references_ (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'syntactic',
    resolved_symbol_id TEXT,
    context_qualified_name TEXT NOT NULL DEFAULT '',
    start_byte INTEGER NOT NULL DEFAULT 0,
    end_byte INTEGER NOT NULL DEFAULT 0,
    start_line INTEGER NOT NULL DEFAULT 0,
    start_column INTEGER NOT NULL DEFAULT 0,
    end_line INTEGER NOT NULL DEFAULT 0,
    end_column INTEGER NOT NULL DEFAULT 0
);
```

- `status`: One of `'syntactic'`, `'resolved'`, `'unresolved'`.

---

### 8. `edges`
Maintains the directed knowledge graph edges between nodes.

```sql
CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    edge_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    file_path TEXT NOT NULL DEFAULT '',
    UNIQUE(edge_type, source_id, target_id)
);
```

- `edge_type`: One of `'CONTAINS'`, `'DEFINES'`, `'IMPORTS'`, `'CALLS'`, `'INHERITS_FROM'`, `'REFERENCES'`.

---

## Schema Stability

Schema version `1` is stable. Any future schema alterations will bump `SCHEMA_VERSION` and require a rebuild via `synapse index --rebuild`.
