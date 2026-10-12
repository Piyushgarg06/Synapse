# Synapse: Repository Intelligence Engine

Synapse is a local-first Repository Intelligence Engine that constructs and maintains a persistent, structured representation of a software codebase. It analyzes source files using Tree-sitter, builds a queryable knowledge graph in SQLite (`.synapse/index.db`), tracks code changes incrementally across Git commits and uncommitted working trees, computes blast-radius deletion impact, and exposes a native Model Context Protocol (MCP) server for AI coding assistants.

---

## 1. Installation

### Requirements
- **Python**: `>= 3.10` (tested on Python 3.10, 3.11, 3.12, 3.13 on Windows, macOS, and Linux)
- **Git**: `git` executable available in `PATH`

### Install from PyPI

Install the official package directly from PyPI:

```bash
pip install synapse-pkg==3.0.1
```

Or install the latest version:

```bash
pip install synapse-pkg
```

### Install from Source

```bash
git clone https://github.com/Piyushgarg06/Synapse.git
cd Synapse
pip install .
```

To install in development/testing mode with dependencies:
```bash
pip install -e .
pip install pytest
```

---

## 2. Quickstart

Run Synapse in any Git repository:

```bash
# 1. Initialize Synapse tracking in the current repository
synapse init

# 2. Build the initial structural index (committed HEAD)
synapse index

# 3. Index uncommitted changes in the active working tree
synapse index --working-tree

# 4. View index health and repository status
synapse status

# 5. Search for symbols or files
synapse search UserService

# 6. Inspect a symbol, its hierarchy, and callers
synapse inspect UserService

# 7. Analyze blast-radius impact before deleting a file or function
synapse delete-info backend/services/user_service.py get_user

# 8. Generate focused, bounded context for LLMs or review
synapse context get_user

# 9. Auto-configure MCP for installed AI tools (Claude, Cursor, Antigravity, Windsurf)
synapse mcp install

# 10. Export the complete index
synapse export json -o index.json
synapse export md -o index.md
synapse export zip -o snapshot.zip
```

---

## 3. Command Reference & Real Outputs

### `synapse init [--mcp]`
Initializes `.synapse/` in the repository root and sets up the SQLite storage schema. Safe and idempotent to re-run on an existing repository without overwriting indexed data.
- `--mcp`: Automatically detects installed AI clients (Claude Desktop, Cursor, Antigravity, Windsurf) and configures MCP server settings.

```bash
$ synapse init
Synapse initialized successfully (schema v1).
```

### `synapse index [--rebuild] [--working-tree] [--json]`
Scans source files and updates the SQLite database.
- **Initial run**: Scans all eligible supported files at `HEAD` and saves a checkpoint.
- **Subsequent runs**: Computes `git diff` against the last checkpoint and updates only added, modified, deleted, or renamed files.
- `--working-tree`: Indexes uncommitted modifications, staged changes, and untracked files in the active working tree without requiring a Git commit. Allows multi-model AI workflows to share updated context.
- `--rebuild`: Forces a complete rebuild from scratch, wiping stale records.
- `--json`: Emits raw indexing statistics as JSON.

```bash
$ synapse index
Indexed 6 files, 9 symbols.
  Files processed: 6
  Symbols found: 9
```

When indexing uncommitted working tree modifications:
```bash
$ synapse index --working-tree
Working tree indexed: 2 files changed, 0 deleted.
```

When run after commits modifying source code:
```bash
$ synapse index
Incremental update: 5 files changed.
  Added: 1, Modified: 2, Deleted: 1, Renamed: 1
```

When run with no changes:
```bash
$ synapse index
Repository unchanged since checkpoint cc17d9d8. Nothing to index.
```

### `synapse status [--json]`
Displays index state, commit checkpoint, error counts, and working tree cleanliness.

```bash
$ synapse status
Synapse Status:
  HEAD commit:    acab2080
  Last indexed:   acab2080
  Up to date:     yes
  Files indexed:  6
  Symbols:        11
  Edges:          27
```

If the working tree has uncommitted modifications:
```bash
$ synapse status
Synapse Status:
  HEAD commit:    acab2080
  Last indexed:   acab2080
  Up to date:     no (working tree dirty)
  Warning: Working tree has uncommitted changes not reflected in the index.
```

### `synapse search <query> [--limit N] [--json]`
Searches symbols (by name and qualified name) and files. Results are ranked by match precision (exact match > prefix match > substring match).

```bash
$ synapse search UserService
Found 2 result(s) for 'UserService':
  class     UserService  (backend/services/user_service.py:3)
  method    UserService.get_user  (backend/services/user_service.py:4)
```

### `synapse inspect <symbol> [--depth N] [--json]`
Inspects a specific symbol's definition, enclosing scope, base classes, subclasses, resolved callers/callees, imports, and unresolved references. Traverses relationships up to `--depth` hops (default: 1).

```bash
$ synapse inspect UserService
Symbol: UserService (class)
  File:     backend/services/user_service.py:3-5
  ID:       57992df372a7a124
  Inherits from:
    - BaseService (backend/base.py:1)
```

If multiple symbols match the query, Synapse reports ambiguity and presents candidate options with locations rather than guessing:
```bash
$ synapse inspect execute
Ambiguous symbol query 'execute'. Multiple symbols match:
  - execute (method) in backend/base.py:3
  - execute (method) in backend/services/worker.py:12
Specify the fully qualified name or refine query.
```

### `synapse context <query> [--max-results N] [--max-bytes N] [--depth N] [-o OUTPUT] [--json]`
Generates a structured, bounded context document around a symbol or query. Includes actual source snippets with line numbers, relationship graph neighbors up to `--depth`, and explicit listings of unresolved dependencies. Detects if disk source files are stale relative to `HEAD`.

```bash
$ synapse context get_user
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

### `synapse delete-info <target> [symbol] [--json]`
Computes the downstream blast-radius impact of deleting or refactoring a file or symbol before making destructive edits. Analyzes `.synapse/index.db` to identify broken external callers, affected subclasses, importers, and references.

```bash
$ synapse delete-info backend/services/user_service.py
Blast Radius Analysis: backend/services/user_service.py
  Target: file (backend/services/user_service.py)
  Defined symbols: 2 (UserService, UserService.get_user)
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

Scope to a single function or method:
```bash
$ synapse delete-info backend/services/user_service.py get_user
Blast Radius Analysis: UserService.get_user
  Target: method (backend/services/user_service.py:4-5)
  Impacted files: 1

Direct Callers Broken:
  - handle_request (backend/controllers/user_controller.py:18)

Summary:
  Deleting UserService.get_user will break 1 caller(s) across 1 file(s).
```

### `synapse export <json|md|zip> [-o OUTPUT]`
Exports canonical index data into portable formats.
- **json**: Full schema-versioned JSON dump containing files, symbols, references, and edges.
- **md**: Deterministic Markdown reference document detailing repository architecture.
- **zip**: Self-contained archive package containing `index.json`, `index.md`, and `README.txt` with deterministic timestamps.

```bash
$ synapse export json -o synapse_export.json
Exported JSON index to synapse_export.json

$ synapse export md -o synapse_export.md
Exported Markdown overview to synapse_export.md

$ synapse export zip -o synapse_export.zip
Exported ZIP snapshot to synapse_export.zip
```

### `synapse mcp [install|uninstall|status]`
Runs the Model Context Protocol (MCP) server or automatically configures MCP settings across AI coding tools and IDEs.

- `synapse mcp`: Starts the stdio JSON-RPC server (used by MCP clients).
- `synapse mcp install [--target TARGET] [--project]`: Auto-detects installed AI tools (Claude Desktop, Claude Code, Cursor, Antigravity, Windsurf, Cline, Roo Code) and adds Synapse MCP configuration.
- `synapse mcp status`: Displays a detection and configuration status matrix across all supported clients.
- `synapse mcp uninstall`: Safely removes Synapse from client configs while preserving other MCP servers.

```bash
# Auto-configure all detected AI clients
$ synapse mcp install
Configuring Synapse MCP for 2 client(s)...
  [+] Antigravity / Gemini   -> ~/.gemini/config/mcp_config.json
  [+] Cursor                 -> ~/.cursor/mcp.json

Successfully configured 2/2 client(s).
Restart your IDE or agent session for changes to take effect.

# Check client status
$ synapse mcp status
Synapse MCP Client Status:
  [+] Configured                 Antigravity / Gemini   (~/.gemini/config/mcp_config.json)
  [+] Configured                 Cursor                 (~/.cursor/mcp.json)
  [*] Detected (not configured)  Claude Desktop         (~/Library/Application Support/Claude/claude_desktop_config.json)
  [-] Not detected               Windsurf               (~/.codeium/windsurf/mcp_config.json)
```

---

## 4. Index Semantics & Architecture

```
Git Repository (HEAD)
       │
  Git Diff (-M -z) ─── Incremental Change Detection
       │
  Tree-sitter ──────── Language Parsers (Python, JS, TS, TSX)
       │
  AST Analyzers ────── Structural Extraction (Symbols, Imports, Inheritance, Calls)
       │
  SQLite Index ─────── Persistent Storage (.synapse/index.db)
       │
  Graph Builder ────── Edge Generation & Cross-File Reference Resolution
       │
  Retrieval Engine ─── Search, Inspect, Context & Deterministic Exports
```

- **Source of Truth**: The Git commit tree at `HEAD` is the authoritative source of truth for repository history.
- **Committed State vs Working Tree**: Synapse indexes committed repository states by default. When `--working-tree` is specified, Synapse parses uncommitted edits, staged changes, and untracked files into `.synapse/index.db`, ensuring that multi-model agent workflows or unfinished code edits share synchronized context.
- **Transactional Updates**: All index writes, deletes, and checkpoint updates occur within atomic SQLite transactions. If a parsing or indexing error occurs mid-run, changes roll back and the checkpoint is not advanced.
- **Zero Modification Guarantee**: Synapse NEVER writes to, modifies, or deletes user source files. All internal metadata resides strictly in `.synapse/index.db`.

---

## 5. Model Context Protocol (MCP) & AI Integration

Synapse includes a native Model Context Protocol (MCP) server over standard I/O (`synapse mcp`), allowing AI coding assistants to query the repository knowledge graph instead of reading entire files or running brute-force grep commands.

### Exposed MCP Tools

| Tool Name | Parameters | Purpose |
|---|---|---|
| `synapse_search` | `query`, `limit` | Find functions, classes, and methods without directory crawls |
| `synapse_inspect` | `symbol`, `depth` | Inspect callers, callees, and inheritance before modifying code |
| `synapse_context` | `symbol`, `budget` | Retrieve bounded, token-budgeted code context bundles |
| `synapse_delete_info` | `target`, `symbol` | Check blast-radius impact and broken callers before deletions |
| `synapse_index` | `working_tree`, `rebuild` | Update `.synapse/index.db` after edits or model switches |
| `synapse_status` | None | Check index health, symbol counts, and dirty state |

### Automatic Client Configuration

Run `synapse mcp install` to automatically detect and configure:
- **Claude Desktop** (`claude_desktop_config.json`)
- **Claude Code CLI** (`~/.claude.json`)
- **Cursor** (`~/.cursor/mcp.json` or `.cursor/mcp.json`)
- **Antigravity / Gemini IDE** (`~/.gemini/config/mcp_config.json`)
- **Windsurf** (`~/.codeium/windsurf/mcp_config.json`)
- **VS Code Extensions** (Cline & Roo Code)

---

## 6. Exclusions & Safety

Synapse automatically excludes paths matching standard ignored patterns:
- Version control metadata: `.git`, `.gitignore`
- Synapse metadata: `.synapse`, `synapse_export.*`
- Virtual environments: `.venv`, `venv`, `env`, `virtualenv`
- Package dependencies: `node_modules`, `site-packages`, `vendor`, `bower_components`
- Build outputs: `dist`, `build`, `out`, `target`, `bin`, `obj`
- Cache directories: `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.cache`, `.parcel-cache`
- Binary and media files: `.exe`, `.dll`, `.so`, `.zip`, `.tar`, `.gz`, `.png`, `.jpg`, `.pdf`, etc.
- Large files exceeding the maximum file size cap (default: 10 MB)

---

## 7. Exit Codes

Synapse adheres to standard UNIX CLI exit codes:
- `0`: Success. Operation completed cleanly.
- `1`: Operational error (e.g., repository not initialized, non-Git directory, corrupt DB, file read error).
- `2`: CLI usage / argument syntax error (e.g., missing required argument, invalid command).

---

## 8. Supported Languages & Extracted Entities

| Language | Extensions | Extracted Symbols | Relationships Captured |
|---|---|---|---|
| **Python** | `.py` | Classes, Methods, Functions | `CONTAINS`, `DEFINES`, `INHERITS_FROM`, `CALLS`, `IMPORTS`, `REFERENCES` |
| **JavaScript** | `.js`, `.jsx`, `.mjs`, `.cjs` | Classes, Methods, Functions | `CONTAINS`, `DEFINES`, `INHERITS_FROM` (class extends), `CALLS`, `IMPORTS`, `REFERENCES` |
| **TypeScript / TSX** | `.ts`, `.tsx` | Classes, Interfaces, Methods, Functions | `CONTAINS`, `DEFINES`, `INHERITS_FROM` (extends / implements), `CALLS`, `IMPORTS`, `REFERENCES` |

---

## 9. Explicit Limitations

Synapse is designed to provide **provable, statically defensible** structural representations without inventing runtime behavior:
- **Dynamic Invocations**: Dynamic dispatch, runtime `getattr()` / `eval()`, dynamic imports (`import()`, `require(variable)`), and metaprogramming constructs remain marked as `unresolved`.
- **Runtime Reflection**: Reflection-based dependency injection and indirect plugin registries cannot be inferred statically.
- **Decorators**: Decorators that mutate function signatures or wrap callable targets are indexed syntactically; runtime wrapper execution paths are not fabricated.
- **Cross-Package Externals**: External package dependencies (e.g., standard library, third-party libraries outside the repository) are identified as module imports, but their external internal symbol graphs are not parsed.
- **Re-exports**: Multi-level star re-exports (`export * from '...'`) across nested modules are tracked up to direct resolvable symbol bindings.

---

## 10. Recovery & Maintenance

If the index database is ever corrupted or state needs to be resynchronized:
```bash
# Force a full rebuild of the repository index from HEAD
synapse index --rebuild
```

If `.synapse/index.db` is physically damaged or truncated:
```bash
# Remove corrupted database file and re-initialize
rm .synapse/index.db
synapse init
synapse index
```

---

## 11. Development & Testing

Synapse includes an exhaustive test suite covering all 9 engineering phases:
```bash
# Run the full test suite
pytest tests/ -v
```

All 82 tests run locally with zero network calls, zero LLM dependencies, and automatic cleanup of temporary Git repositories.

---

## 12. License

MIT License. See [LICENSE](LICENSE) for details.
