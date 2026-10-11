---
title: Error Messages
description: Complete catalogue of Synapse CLI error messages, causes, and solutions
---

# Error Messages

This page documents every error message emitted by Synapse, including its cause and the concrete command to resolve it.

---

## Catalogue of Error Messages

### 1. `Error: Not in a git repository.`
- **Emitting Location**: `synapse/cli.py:21`
- **Cause**: A Synapse command was executed in a directory that is not managed by Git.
- **Fix**: Initialize a Git repository with `git init` or navigate to an existing Git repository.

---

### 2. `Error: Synapse not initialized. Run 'synapse init' first.`
- **Emitting Location**: `synapse/cli.py:72, 96, 126, 161, 258`
- **Cause**: A subcommand (`status`, `search`, `inspect`, `context`, or `export`) was invoked before `synapse init` was run.
- **Fix**: Run `synapse init` to create `.synapse/index.db`.

---

### 3. `Synapse directory exists but database is corrupt: <detail>`
- **Emitting Location**: `synapse/core.py:46`, `synapse/cli.py:33`
- **Cause**: The file at `.synapse/index.db` is not a valid SQLite database or has unreadable headers.
- **Fix**: Force a rebuild with `synapse index --rebuild`, or delete `.synapse/index.db` and run `synapse init`.

---

### 4. `Error: Unknown export format '<format>'`
- **Emitting Location**: `synapse/cli.py:290`
- **Cause**: The format argument supplied to `synapse export` is not one of the allowed choices.
- **Fix**: Specify `json`, `md`, or `zip`.

---

### 5. `Error: writing output file: <detail>`
- **Emitting Location**: `synapse/cli.py:244`
- **Cause**: The path passed to `-o` or `--output` points to a non-existent directory or lacks filesystem write permissions.
- **Fix**: Ensure the destination directory exists and has write permissions.

---

### 6. `No results found for '<query>'.`
- **Emitting Location**: `synapse/cli.py:110`
- **Cause**: No symbol or file matched the search query.
- **Fix**: Check spelling or verify that the target file has not been excluded.

---

### 7. `Symbol '<symbol>' not found.`
- **Emitting Location**: `synapse/retrieval/engine.py:116`
- **Cause**: The target symbol name is not defined in any indexed source file.
- **Fix**: Search for the symbol using `synapse search` to confirm its declaration and qualified name.

---

### 8. `Ambiguous symbol query '<symbol>'. Multiple symbols match:`
- **Emitting Location**: `synapse/retrieval/engine.py:135`
- **Cause**: Multiple symbols in different files share the same name.
- **Fix**: Re-run `synapse inspect` using the fully qualified name (such as `ClassName.methodName` or `ModuleName.functionName`).

---

### 9. `File too large (<size> bytes, max 10485760)`
- **Emitting Location**: `synapse/analysis/dispatcher.py:51`
- **Cause**: A source file exceeds the 10 MB maximum size cap.
- **Fix**: Exclude large bundle artifacts or split oversized files into smaller modules.
