# Synapse MCP Server Instructions & Best Practices

## Core Principle: Use `index.db` as Your Primary Repository Context

Synapse maintains a persistent, deterministic code knowledge graph inside `.synapse/index.db` (SQLite database). 

**ALWAYS look at `index.db` first for repository context** instead of reading dozens of raw files or guessing file contents. The `index.db` database contains pre-computed, verified structural knowledge about what every file does, every function/class defined, and how components interact across the entire codebase.

---

## What `index.db` Tells You About the Codebase

The `.synapse/index.db` database stores the full knowledge graph across several relational tables:

1. **`files`**: Maps out all source files in the project, their languages, and parse status.
2. **`symbols`**: Every function, method, class, and interface with exact byte and line ranges (`start_line` to `end_line`), qualified names, and parent scopes.
3. **`calls`**: Exact static call hierarchy (which functions call which other functions across files).
4. **`inheritance`**: Class hierarchies (which classes inherit from which base classes).
5. **`imports`**: Precise module imports, imported symbols, and aliases between files.
6. **`references_`**: Resolved symbol references pointing to their true definition IDs.
7. **`edges`**: Directed graph edges connecting nodes: `CONTAINS`, `DEFINES`, `CALLS`, `INHERITS_FROM`, `IMPORTS`, and `REFERENCES`.

---

## How AI Assistants Must Use Synapse Tools to Query `index.db`

### 1. Finding "What Files Do What" & Locating Code
- **Call `synapse_search(query)`**:
  - Searches `index.db` instantly by symbol name, method, class, or file path.
  - Returns exact qualified names, kinds (`function`, `class`, `method`), and file locations.
  - **Rule**: Do not perform blind filesystem scans; use `synapse_search` to pinpoint targets directly from `index.db`.

### 2. Understanding Function/Class Architecture & Call Graphs
- **Call `synapse_inspect(symbol, depth)`**:
  - Extracts the symbol's exact location, docstring, outgoing callees, incoming callers, and inheritance trees from `index.db`.
  - Use `depth=1` to see direct callers/callees, or `depth=2` for multi-hop architectural dependencies.
  - **Rule**: Never edit a function or method without first inspecting its callers in `index.db`.

### 3. Extracting High-Density Context for LLM Prompting
- **Call `synapse_context(symbol, budget, depth)`**:
  - Pulls structured, token-bounded context directly from `index.db` containing the target definition, relevant imported types, base classes, and caller snippets.
  - Prevents context window exhaustion by avoiding massive raw file dumps.
  - Automatically flags if working tree edits make any snippets stale.

### 4. Blast Radius Analysis Before Editing or Deleting
- **Call `synapse_delete_info(target, symbol)`**:
  - Uses `index.db` to calculate the blast radius of removing or refactoring a file or symbol.
  - Lists:
    - Every file that imports the target module.
    - Every external caller that would break.
    - Every subclass that would lose its base.
    - Every resolved reference that would become dangling.
  - **Rule**: Run `synapse_delete_info` before refactoring or deleting to ensure zero unintended breakage.

### 5. Multi-Model Collaboration & Working-Tree Indexing
- **Call `synapse_index(working_tree=True)`**:
  - Whenever you create new files or modify existing ones without committing to git, call `synapse_index(working_tree=True)`.
  - This immediately indexes uncommitted changes into `index.db` so the next model or conversational turn sees the updated repository state without lost context.

---

## Direct Database Access (When Needed)
If you have access to a database tool or SQLite shell, you can also query `.synapse/index.db` directly to examine symbol distributions, find all methods belonging to a class, or trace complex graph traversals using SQL queries.
