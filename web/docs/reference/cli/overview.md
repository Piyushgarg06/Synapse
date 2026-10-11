---
title: CLI Overview
description: Overview of the Synapse command-line interface commands and syntax
---

# CLI Overview

Synapse provides eight commands for initializing, indexing, inspecting, querying, and exporting repository structural intelligence.

---

## Global Synopsis

```
synapse [-h] {init,index,status,search,inspect,context,export} ...
```

---

## Commands Summary

| Command | Purpose | Reads | Writes |
|---|---|---|---|
| [`synapse init`](/reference/cli/init) | Initialize Synapse in a Git repository | `.git`, `.synapse/index.db` | `.synapse/`, `.synapse/index.db`, `.synapse/.gitignore` |
| [`synapse index`](/reference/cli/index) | Index repository files incrementally or full rebuild | Git tree, source files, `.synapse/index.db` | `.synapse/index.db` |
| [`synapse status`](/reference/cli/status) | Show index state, checkpoint, and dirty status | Git status, `.synapse/index.db` | None |
| [`synapse search`](/reference/cli/search) | Search for symbols and files by name | `.synapse/index.db` | None |
| [`synapse inspect`](/reference/cli/inspect) | Inspect a symbol, its hierarchy, and callers | `.synapse/index.db` | None |
| [`synapse context`](/reference/cli/context) | Retrieve focused, bounded source context | `.synapse/index.db`, source files on disk | Optional output file (`-o`) |
| [`synapse export`](/reference/cli/export) | Export index data to JSON, Markdown, or ZIP | `.synapse/index.db` | Optional output file (`-o`) |

---

## Standard Options

All commands accept `-h` or `--help` to print usage information:

```bash
synapse <command> --help
```

---

## Safety Guarantee

Synapse commands **never write to or modify tracked user source files**. All persistent data is stored strictly in `.synapse/index.db`.
