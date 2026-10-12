---
title: synapse mcp
description: Reference documentation for the synapse mcp command and auto-installer
---

# synapse mcp

Starts the Model Context Protocol (MCP) server or automatically configures MCP across supported AI tools and IDEs.

---

## Synopsis

```
synapse mcp [-h] {install,uninstall,status} ...
```

---

## Description

`synapse mcp` operates in two primary modes:

1. **Protocol Server Mode (Default)**: When invoked without subcommands (`synapse mcp`), it starts a JSON-RPC server on standard input/output conforming to the Model Context Protocol specification. AI coding assistants (Claude Code, Cursor, Antigravity, Windsurf) connect to this process to query repository intelligence.
2. **Configuration Mode**: Subcommands manage client JSON configuration files across user settings directories, eliminating manual JSON edits.

Properties:
- **Reads**: `.synapse/index.db`, client configuration files
- **Writes**: Client JSON configuration files (when running `install` or `uninstall`)
- **Never touches**: Source code files in the repository

---

## Subcommands

| Subcommand | Description |
|---|---|
| [`install`](#synapse-mcp-install) | Auto-detect installed AI tools and add Synapse MCP server settings |
| [`uninstall`](#synapse-mcp-uninstall) | Remove Synapse MCP server settings from client configs |
| [`status`](#synapse-mcp-status) | Display detection and configuration status across all supported clients |

---

## synapse mcp install

Auto-detects supported AI tools and writes configuration blocks to their settings files.

### Synopsis

```
synapse mcp install [-h] [--target TARGET] [--project]
```

### Options

| Option | Type | Default | Description |
|---|---|---|---|
| `--target` | String | `all` | Specific client: `all`, `antigravity`, `cursor`, `claude-desktop`, `claude-code`, `windsurf`, `cline`, `roo` |
| `--project` | Flag | `False` | Configure current workspace (`.cursor/mcp.json`, `.agents/mcp_config.json`) instead of global user settings |
| `-h`, `--help` | Flag | N/A | Show help message and exit |

---

## synapse mcp uninstall

Removes Synapse MCP configuration from client settings while preserving other configured servers.

### Synopsis

```
synapse mcp uninstall [-h] [--target TARGET] [--project]
```

### Options

| Option | Type | Default | Description |
|---|---|---|---|
| `--target` | String | `all` | Specific client target to remove |
| `--project` | Flag | `False` | Remove from current workspace instead of global user settings |
| `-h`, `--help` | Flag | N/A | Show help message and exit |

---

## synapse mcp status

Displays a table showing which clients are installed on the local system and whether Synapse MCP is configured.

### Synopsis

```
synapse mcp status [-h] [--project]
```

### Example Status Output

```
Synapse MCP Client Status:
  [+] Configured                 Antigravity / Gemini   (/home/user/.gemini/config/mcp_config.json)
  [+] Configured                 Cursor                 (/home/user/.cursor/mcp.json)
  [*] Detected (not configured)  Claude Desktop         (/home/user/.config/Claude/claude_desktop_config.json)
  [-] Not detected               Windsurf               (/home/user/.codeium/windsurf/mcp_config.json)
```

---

## Tools Exposed Over MCP

When connected via MCP, Synapse provides six structured tools:

| Tool Name | Parameters | Description |
|---|---|---|
| `synapse_search` | `query`, `repo_path`, `limit` | Searches symbols and file paths in `.synapse/index.db` |
| `synapse_inspect` | `symbol`, `repo_path`, `depth` | Returns definition, callers, callees, and class hierarchy |
| `synapse_context` | `symbol`, `repo_path`, `depth`, `budget` | Returns bounded snippet bundles for prompt construction |
| `synapse_delete_info` | `target`, `symbol`, `repo_path` | Evaluates blast-radius impact and broken external callers |
| `synapse_index` | `repo_path`, `working_tree`, `rebuild` | Indexes repository or uncommitted working tree changes |
| `synapse_status` | `repo_path` | Returns indexed symbol counts, graph edges, and dirty status |

---

## Supported Clients and Config Paths

| Client | Global Configuration Path |
|---|---|
| **Antigravity / Gemini** | `~/.gemini/config/mcp_config.json` |
| **Cursor** | `~/.cursor/mcp.json` or `.cursor/mcp.json` |
| **Claude Desktop** | macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`<br>Windows: `%APPDATA%\Claude\claude_desktop_config.json`<br>Linux: `~/.config/Claude/claude_desktop_config.json` |
| **Claude Code** | `~/.claude.json` |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` |
| **Cline (VS Code)** | `Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json` |
| **Roo Code (VS Code)** | `Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json` |

---

## Examples

### Example 1 - Automatic Multi-Client Configuration

Detect installed clients and configure Synapse for all of them:

```bash
synapse mcp install
```

### Example 2 - Project-Specific Cursor Configuration

Write configuration to `.cursor/mcp.json` inside the current repository:

```bash
synapse mcp install --target cursor --project
```

### Example 3 - Verification

Verify which clients have active Synapse connections:

```bash
synapse mcp status
```
