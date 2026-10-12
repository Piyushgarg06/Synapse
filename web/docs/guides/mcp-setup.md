---
title: AI Agent Setup via MCP
description: How to connect Synapse to Claude Code, Cursor, Antigravity, Windsurf, Cline, and Roo Code using Model Context Protocol
---

# AI Agent Setup via MCP

Synapse implements the Model Context Protocol (MCP) standard, exposing repository structural analysis, retrieval, and impact calculation to AI coding tools.

---

## Architecture Overview

When an agent works in a large repository, standard directory listings and text grep searches consume excessive context tokens and produce inaccurate relationship maps. Synapse replaces manual file crawling by exposing its SQLite knowledge graph (`.synapse/index.db`) directly through structured MCP tools.

```
┌────────────────────────────────────────────────────────┐
│  AI Coding Client (Claude Code / Cursor / Windsurf)    │
└──────────────────────────┬─────────────────────────────┘
                           │ JSON-RPC over stdio
┌──────────────────────────▼─────────────────────────────┐
│  Synapse MCP Server (`synapse mcp`)                    │
└──────────────────────────┬─────────────────────────────┘
                           │ SQLite queries
┌──────────────────────────▼─────────────────────────────┐
│  Repository Knowledge Graph (`.synapse/index.db`)      │
└────────────────────────────────────────────────────────┘
```

---

## Automated Configuration

The Synapse CLI includes an automated configuration utility that detects installed AI IDEs and updates their settings files.

### Step 1 - Install Synapse

Install the Synapse package:

```bash
pip install synapse-pkg
```

### Step 2 - Auto-Configure Detected Clients

Run the configuration installer from the repository root:

```bash
synapse mcp install
```

The command checks standard configuration directories on macOS, Linux, and Windows:

```
Configuring Synapse MCP for 2 client(s)...
  [+] Antigravity / Gemini   -> ~/.gemini/config/mcp_config.json
  [+] Cursor                 -> ~/.cursor/mcp.json

Successfully configured 2/2 client(s).
Restart your IDE or agent session for changes to take effect.
```

### Step 3 - Check Configuration Status

Inspect which clients are active and configured:

```bash
synapse mcp status
```

---

## Project-Level Configuration

To configure settings strictly within a specific repository rather than globally in user home directories, use the `--project` flag:

```bash
synapse mcp install --target cursor --project
```

This creates `.cursor/mcp.json` in the current working directory:

```json
{
  "mcpServers": {
    "synapse": {
      "command": "synapse",
      "args": ["mcp"]
    }
  }
}
```

---

## Manual Configuration Reference

If using a custom tool or configuring environments manually, insert the following block into your tool's MCP configuration file:

### Standard MCP Configuration Schema

```json
{
  "mcpServers": {
    "synapse": {
      "command": "synapse",
      "args": ["mcp"]
    }
  }
}
```

### File Locations by Client

| Client | Platform | Target Configuration Path |
|---|---|---|
| **Antigravity / Gemini** | All | `~/.gemini/config/mcp_config.json` |
| **Cursor** | All | `~/.cursor/mcp.json` or `.cursor/mcp.json` |
| **Claude Desktop** | macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| | Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| | Linux | `~/.config/Claude/claude_desktop_config.json` |
| **Claude Code** | All | `~/.claude.json` |
| **Windsurf** | All | `~/.codeium/windsurf/mcp_config.json` |
| **Cline (VS Code)** | All | `Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json` |
| **Roo Code (VS Code)**| All | `Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json` |

---

## MCP Tools Reference

Once connected, your AI assistant gains access to six structured tools:

### `synapse_search`
- **Purpose**: Search functions, classes, methods, and files by name.
- **Parameters**: `query` (string), `limit` (integer).
- **Usage**: Used by agents instead of `grep` or file listings to find where symbols are declared.

### `synapse_inspect`
- **Purpose**: Inspect detailed definition locations, class inheritance, callers, and callees.
- **Parameters**: `symbol` (string), `depth` (integer).
- **Usage**: Used before modifying an existing function to identify all incoming calls.

### `synapse_context`
- **Purpose**: Retrieve token-budgeted snippet bundles containing the target definition and immediate dependencies.
- **Parameters**: `symbol` (string), `budget` (integer), `depth` (integer).
- **Usage**: Provides high-signal context for code generation without reading entire files.

### `synapse_delete_info`
- **Purpose**: Compute blast-radius impact before modifying or deleting code.
- **Parameters**: `target` (file or symbol), `symbol` (optional scope).
- **Usage**: Informs the agent of every downstream file that will break if a file or function is deleted.

### `synapse_index`
- **Purpose**: Re-index the repository or working tree on demand.
- **Parameters**: `working_tree` (boolean, default `true`), `rebuild` (boolean).
- **Usage**: Allows the agent to update `.synapse/index.db` after making code changes.

### `synapse_status`
- **Purpose**: Query index counts, graph edges, and uncommitted modifications.
- **Usage**: Provides metadata on current repository tracking state.

---

## Handling Uncommitted Changes Across Models

When switching between different AI models or agent sessions, uncommitted edits can leave secondary models without context.

Synapse addresses this with the working tree flag:

```bash
synapse index --working-tree
```

When called, Synapse indexes modified, staged, and untracked files on disk into `.synapse/index.db` without requiring a Git commit. Any subsequent model session queries the updated working tree state immediately.
