---
title: synapse init
description: Reference documentation for the synapse init command
---

# synapse init

Initializes Synapse tracking and SQLite storage in a Git repository.

---

## Synopsis

```
synapse init [-h] [--mcp]
```

---

## Description

`synapse init` prepares the repository for indexing by creating the `.synapse/` directory and applying the database schema in `.synapse/index.db`.

Passing `--mcp` automatically detects installed AI tools (Claude Desktop, Cursor, Antigravity, Windsurf) and writes configuration settings so agents can query the repository immediately.

- **Reads**: `.git/` metadata to verify the repository root; existing `.synapse/index.db` if present.
- **Writes**: `.synapse/` directory, `.synapse/index.db`, `.synapse/.gitignore` (containing `*`).
- **Never touches**: Tracked user source files, Git configuration, or Git commit history.

---

## Options

| Option | Type | Default | Description |
|---|---|---|---|
| `--mcp` | Flag | `False` | Auto-configure MCP settings for detected AI IDEs and clients |
| `-h`, `--help` | Flag | N/A | Show help message and exit |

---

## Output

### Initial run
```
Synapse initialized successfully (schema v1).
```

### Repeated run
Running `synapse init` repeatedly on an already initialized repository is safe and does not overwrite existing data:
```
Synapse already initialized (schema v1). Existing data preserved.
```

---

## Exit Codes

| Code | Condition |
|---|---|
| `0` | Success (new initialization or existing database verified) |
| `1` | Operational error (not inside a Git repository, or existing database file is corrupted) |
| `2` | Unknown command line option specified |

---

## Errors and Diagnostics

### Not in a Git repository
```
Error: Not in a git repository.
```
- **Cause**: Command executed outside a Git repository.
- **Fix**: Run `git init` or change directory to a Git repository.

### Corrupted database
```
Error: Synapse directory exists but database is corrupt: file is not a database
```
- **Cause**: `.synapse/index.db` exists but contains invalid or truncated data.
- **Fix**: Remove `.synapse/index.db` and run `synapse init`.

---

## Examples

### Example 1: First-time initialization
```bash
$ synapse init
Synapse initialized successfully (schema v1).
```

### Example 2: Idempotent re-initialization
```bash
$ synapse init
Synapse already initialized (schema v1). Existing data preserved.
```
