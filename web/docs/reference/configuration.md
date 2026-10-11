---
title: Configuration
description: Complete settings, constants, and default values in Synapse
---

# Configuration

Synapse uses zero-configuration defaults derived directly from your repository and Git metadata.

---

## Storage and Paths

| Setting | Value / Location | Code Source | Description |
|---|---|---|---|
| Index Directory | `.synapse/` | `synapse/core.py:21` | Hidden folder in repository root containing index artifacts |
| Database Path | `.synapse/index.db` | `synapse/core.py:22` | Embedded SQLite persistent storage file |
| Schema Version | `1` | `synapse/index.store.py:9` | Schema version stored in `state` table |
| Gitignore Path | `.synapse/.gitignore` | `synapse/core.py:49` | Automatically populated with `*` to prevent index commits |

---

## File Size Limits

| Parameter | Default Value | Code Source | Description |
|---|---|---|---|
| `MAX_FILE_SIZE` | `10 MB` (`10,485,760` bytes) | `synapse/parsing/parser.py:75` | Files larger than this are skipped and flagged with a parse error |

---

## SQLite Database Configuration

| Pragma | Value | Code Source | Description |
|---|---|---|---|
| `journal_mode` | `WAL` | `synapse/index/store.py:12` | Write-Ahead Logging for high concurrency |
| `foreign_keys` | `ON` | `synapse/index/store.py:13` | Cascading deletions when files are removed |

---

## Command Defaults

| Command | Parameter | Default Value | Description |
|---|---|---|---|
| `synapse search` | `--limit` | `20` | Max search results returned |
| `synapse inspect` | `--depth` | `1` | Graph traversal depth |
| `synapse context` | `--max-results` | `10` | Max context items returned |
| `synapse context` | `--max-bytes` | `8192` | Max bytes per source snippet |
| `synapse context` | `--depth` | `2` | Traversal depth for callers and callees |
| `synapse export zip` | `-o` | `synapse_export.zip` | Default output path when omitted |
