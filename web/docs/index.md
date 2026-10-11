---
title: Synapse
description: Local-first Repository Intelligence Engine for codebases
---

# Synapse: Repository Intelligence Engine

Synapse is a local-first CLI tool that parses code repositories using Tree-sitter, stores symbols and relationships in an embedded SQLite index, and tracks changes across Git commits. It provides deterministic retrieval and context synthesis for developers and AI code assistants without running code or contacting external networks.

<InteractiveGraph />

---

## Command Demonstration

The session below shows initializing Synapse on a multi-language repository, running the initial index, inspecting a class hierarchy, and generating bounded context.

<TerminalPlayer title="Full Session on Sample Repository" />

---

## Core Characteristics

- **Local-first execution**: All metadata resides in `.synapse/index.db`. No network requests, vector databases, or background daemons are used.
- **Git integration**: Synapse indexes committed repository states at `HEAD`. Incremental updates use `git diff -M -z` to re-parse only changed files.
- **Abstract syntax tree parsing**: Supports Python, JavaScript, TypeScript, and TSX through pinned Tree-sitter grammar binaries.
- **Defensible graph edges**: Relationships (`CALLS`, `INHERITS_FROM`, `CONTAINS`, `IMPORTS`) are emitted only when verifiable through static analysis. Dynamic and external calls remain marked as unresolved.
- **Deterministic exports**: Emits portable JSON, Markdown, and ZIP snapshots with reproducible checksums.

---

## Navigation Paths

- To install the CLI, visit [Installation](/getting-started/installation).
- For a step-by-step walkthrough, see [Quickstart](/getting-started/quickstart).
- For architectural mechanics, see [How Synapse Works](/concepts/how-synapse-works).
- For flag specifications and exit codes, see [CLI Reference](/reference/cli/overview).
