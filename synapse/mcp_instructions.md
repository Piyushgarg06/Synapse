# Synapse MCP Server Instructions & Best Practices

Synapse is a local-first, zero-network repository intelligence engine. It builds a persistent code knowledge graph using Tree-sitter and SQLite, indexing symbols, call edges, class inheritance hierarchies, imports, and cross-file references.

## Recommended Workflow for AI Assistants (Claude Code, Gemini, Codex, Cursor)

### 1. Code Exploration & Discovery
- **`synapse_search`**: Always search for functions, classes, methods, or file paths using Synapse before guessing file paths or manually listing directories.
- Returns exact file paths, line ranges, and qualified symbol names.

### 2. Architecture & Dependency Inspection
- **`synapse_inspect`**: Before modifying a function or class, inspect it to see:
  - Definition location (file, start and end lines).
  - Callers (incoming callers across the repository).
  - Callees (outgoing functions called by this symbol).
  - Inheritance hierarchy (base classes and subclasses).
- Use `depth=1` for immediate callers/callees, or `depth=2` for two-hop dependency chains.

### 3. High-Density Context Gathering
- **`synapse_context`**: Rather than reading entire files into your prompt, use `synapse_context` to get a token-bounded, high-density snippet bundle containing the target symbol and its immediate callers/dependencies.
- It respects the token budget and automatically flags if any working tree changes make snippets stale.

### 4. Safe Refactoring & Deletion
- **`synapse_delete_info`**: ALWAYS run this before deleting or renaming a file or function.
- It computes the blast radius and lists:
  - Every external file that imports from it.
  - Every external caller that would break.
  - Every subclass that would lose its base.
  - Every resolved reference that would be severed.
- If `affected_file_count == 0`, it is safe to remove. Otherwise, review and update the affected files identified by the tool.

### 5. Multi-Model Collaboration & Working-Tree Sync
- **`synapse_index`**: When you make changes to files on disk without committing, run `synapse_index(working_tree=True)` so subsequent queries and other AI models reflect your uncommitted edits immediately.
