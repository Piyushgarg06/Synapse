# Frequently Asked Questions

This page addresses operational questions regarding Synapse behavior, storage, and indexing guarantees.

## Data Privacy and Network Usage

### Remote Servers and Network Activity

No. Synapse is a local-first CLI tool. It makes zero network calls, does not bundle telemetry, and does not communicate with external APIs. All indexing operations, AST parsing, graph queries, and SQLite writes occur entirely on your local machine.

## Git Integration

### Uncommitted and Untracked Files

No. Synapse indexes only files committed to Git at `HEAD`. Staged changes, modified working tree files, and untracked files are ignored. To include new or edited symbols in the index, commit your changes before executing `synapse index`.

### Operating Outside a Git Repository

No. Synapse requires an initialized Git repository. The incremental engine relies on Git commit graphs and `git diff-tree` to track file mutations deterministically. Attempting to run `synapse init` outside a Git repository exits with status code 1.

### Index State During Branch Switches

When you switch branches with `git checkout` or `git switch`, the working tree commit differs from the last indexed commit recorded in `.synapse/index.db`. Running `synapse status` detects this difference and reports the index as stale. Running `synapse index` then computes the diff between the recorded commit and the new `HEAD`, updating modified files incrementally.

## Parsing and Analysis

### Syntax Error Handling During Parsing

Synapse uses Tree-sitter for AST parsing. Tree-sitter provides error-recovery capabilities that allow parsing to continue past syntax errors in many instances. If a file is completely unparseable, Synapse logs an error for that specific file, skips its symbols, and completes indexing for all remaining files.

### Unresolved External Libraries

Synapse indexes source files located within the target repository boundaries. Third-party packages installed in virtual environments or `node_modules` are outside the repository root and are not parsed. Identifiers referencing external packages are classified as unresolved external symbols.

### Static Analysis and Type Evaluation Boundaries

No. Synapse performs static AST analysis only. It does not run Python interpreters, Node.js engines, or dynamic linkers. It extracts declarations and references visible directly in the syntax tree without evaluating runtime behavior.

## CLI Behavior

### Distinction Between Inspect and Search

`synapse search` performs substring and trigram matching across all indexed symbol names and file paths, returning a ranked list of candidate matches. `synapse inspect` retrieves detailed structural information for an exact symbol name, including its enclosing scope, line bounds, and inbound/outbound references up to a specified graph depth.

### Exit Code Structure

Synapse uses standard POSIX exit codes:
- `0`: Operation completed successfully.
- `1`: Operational error (missing repository, uninitialized database, file I/O error, corrupt index).
- `2`: Invalid CLI arguments or unrecognized options.
