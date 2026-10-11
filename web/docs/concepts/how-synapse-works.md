---
title: How Synapse Works
description: The pipeline from source code to knowledge graph and retrieval
---

# How Synapse Works

Synapse converts code into an queryable knowledge graph through a deterministic six-stage pipeline without executing user code or calling external networks.

<PipelineDiagram />

---

## Pipeline Execution Stages

### 1. Git Change Detection
Synapse invokes the local Git CLI with `-c core.quotepath=false` to read the repository state. On an initial index, it retrieves all tracked files using `git ls-files -z`. On subsequent runs, it runs `git diff --name-status -M -z <checkpoint> HEAD` to identify added, modified, deleted, and renamed files.

### 2. Tree-sitter Parsing
Eligible files are read as raw bytes and parsed using official Tree-sitter language bindings (`tree-sitter-python`, `tree-sitter-javascript`, `tree-sitter-typescript`). Files exceeding 10 MB are rejected before parsing to prevent unbounded memory usage.

### 3. Structural AST Analysis
Language-specific visitors traverse the concrete syntax tree to extract:
- Declared classes, methods, interfaces, and standalone functions.
- Class inheritance hierarchies (statically specified base classes).
- Call expressions within functional and method bodies.
- Import statements, namespace imports, and aliases.

### 4. SQLite Persistence
Extracted entities are committed to `.synapse/index.db` using SQLite in Write-Ahead Logging (WAL) mode with foreign key constraints enabled. All writes for an update occur within a single database transaction.

### 5. Knowledge Graph Construction
The graph builder correlates calls and base classes across files. When a call target matches a known symbol defined within the repository, a `CALLS` edge is recorded. Targets that cannot be statically resolved are preserved as unresolved references.

### 6. Retrieval and Synthesis
Retrieval commands query SQLite tables using indexed lookups. Search uses tiered ranking (exact match, prefix match, substring match). Inspection traverses graph edges up to a specified depth. Context generation extracts verified source snippets and flags whether the working tree file has drifted from the index checkpoint.

---

## What Synapse Stores

The index records:
- Tracked file paths, languages, and parse error flags.
- Symbol names, qualified names, kinds, line numbers, and byte coordinates.
- Import module names, imported symbols, and aliases.
- Explicit base classes and interface names.
- Call sites and caller-callee pairings.
- Directed graph edges: `CONTAINS`, `DEFINES`, `IMPORTS`, `CALLS`, `INHERITS_FROM`, and `REFERENCES`.
- Commit checkpoints for incremental change tracking.

---

## What Synapse Never Stores

Synapse does not store:
- Full file contents or duplicate copies of source trees.
- Inferred runtime types from speculative execution.
- Third-party library internal ASTs outside repository boundaries.
- Embeddings or vector database indexes.
- Dynamic runtime dispatches (`getattr`, `eval`, or reflection).

---

## Related Reference

- For detailed SQLite table structures, see [Storage Schema](/reference/storage-schema).
- For exclusion behavior, see [Default Exclusions](/reference/exclusions).
- For command options, see [CLI Reference](/reference/cli/overview).
