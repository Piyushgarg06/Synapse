# Contributor Architecture

This document describes the internal architecture of Synapse, detailing module responsibilities, data flow through the indexing pipeline, the extension model for language analyzers, and test execution.

## Module Map

The codebase is organized under `synapse/`:

```
synapse/
├── cli.py               # CLI entry point, argument parsing, output formatting
├── core.py              # Indexing orchestration, transaction management
├── models.py            # Data classes (Symbol, Reference, FileMetadata)
├── exclusions.py        # Default exclusion rules and .synapseignore parser
├── git/
│   └── ops.py           # Git operations: repository detection, diffs, tree reads
├── parsing/
│   └── parser.py        # Tree-sitter parser initialization and tree building
├── analysis/
│   ├── dispatcher.py    # Language routing based on file extension
│   ├── python_analyzer.py
│   ├── js_analyzer.py
│   └── ts_analyzer.py
├── graph/
│   └── builder.py       # Cross-file reference resolution and graph edges
├── index/
│   └── store.py         # SQLite schema, transactions, and persistence
├── retrieval/
│   └── engine.py        # Search, symbol inspection, context assembly
└── export/
    └── exporter.py      # Serializers for JSON, Markdown, and ZIP exports
```

## Indexing Data Flow

When `synapse index` executes, execution flows through the following pipeline:

1. **Git State Verification (`synapse/git/ops.py`)**:
   - Verifies the current working directory is inside a Git repository.
   - Retrieves the current commit SHA at `HEAD`.
   - Reads the last indexed commit SHA from `metadata` in `.synapse/index.db`.

2. **Change Detection**:
   - If no prior commit is recorded or `--rebuild` is supplied, Synapse enumerates all files tracked by Git at `HEAD`.
   - On subsequent runs, Synapse executes `git diff-tree -r --name-status <old_sha> <new_sha>` to detect added, modified, renamed, and deleted files.

3. **Exclusion and Filtering (`synapse/exclusions.py`)**:
   - Files matching default patterns (such as `node_modules`, `.git`, `__pycache__`) or `.synapseignore` are excluded.
   - Files exceeding 10 MB (10,485,760 bytes) are skipped with a logged warning.

4. **AST Extraction (`synapse/parsing/` and `synapse/analysis/`)**:
   - The raw byte content of each file is parsed into a Tree-sitter syntax tree.
   - The language dispatcher selects the corresponding analyzer (`python_analyzer.py`, `js_analyzer.py`, or `ts_analyzer.py`).
   - The analyzer walks the AST, extracting symbol definitions (classes, functions, methods, interfaces), imports, exports, and invocation references.

5. **Relational Persistence (`synapse/index/store.py`)**:
   - File records, symbols, and raw references are written to SQLite inside an atomic transaction.
   - For incremental updates, existing symbol and reference rows for modified or deleted files are cleared before inserting new records.

6. **Graph Resolution (`synapse/graph/builder.py`)**:
   - Unresolved call references are matched against symbol declarations within the repository.
   - Import aliases and module paths are resolved to target file paths.
   - Graph edges are committed to SQLite, linking calling symbols to definition symbols.

7. **Commit Checkpoint Update**:
   - If all files process without error, the current `HEAD` commit SHA is written to the `metadata` table, committing the transaction.
   - If an unhandled error occurs during indexing, the SQLite transaction is rolled back, preserving the prior valid state.

## Adding a Language Analyzer

To add support for a new programming language:

1. **Add the Tree-sitter Grammar Dependency**:
   - Add the corresponding Tree-sitter grammar package to `pyproject.toml` (for example, `tree-sitter-go`).

2. **Register the Language in `synapse/parsing/parser.py`**:
   - Map the language identifier to the Tree-sitter language object.

3. **Implement the Analyzer**:
   - Create a new analyzer module in `synapse/analysis/` (for example, `go_analyzer.py`).
   - Inherit from or implement the base analyzer interface:
     - `extract_symbols(tree, file_path)`: Returns a list of `Symbol` instances.
     - `extract_references(tree, file_path)`: Returns a list of `Reference` instances.
     - `extract_imports(tree, file_path)`: Returns a list of import statements and bindings.

4. **Register File Extensions in `synapse/analysis/dispatcher.py`**:
   - Add file extensions to the dispatch dictionary mapping extensions to the new analyzer class.

5. **Add Test Coverage**:
   - Create test fixtures in `tests/` verifying symbol extraction, function calls, class or struct definitions, and import resolution for the new language.

## Running the Test Suite

Synapse uses `pytest` for unit and integration testing.

Run all tests:

```bash
pytest
```

Run with verbose output and test execution durations:

```bash
pytest -v --durations=10
```

Run tests for a specific module:

```bash
pytest tests/test_analysis.py
```
