# Command Cheat Sheet

A concise reference table of all Synapse commands, options, and exit codes.

## CLI Commands

### Repository Lifecycle

```bash
# Initialize Synapse storage in the current Git repository
synapse init

# Index all supported files at HEAD
synapse index

# Force a complete re-index of all files from scratch
synapse index --rebuild

# Output indexing progress and summary in JSON format
synapse index --json

# Check index freshness against current HEAD commit
synapse status

# Return status summary as JSON
synapse status --json
```

### Search and Inspection

```bash
# Search symbols and files matching a query string
synapse search <query>

# Limit search results to N items (default: 20)
synapse search <query> --limit 10

# Return search results as structured JSON
synapse search <query> --json

# Inspect symbol declarations and reference graph (default depth: 1)
synapse inspect <symbol>

# Traverse reference graph up to depth N
synapse inspect <symbol> --depth 2

# Output inspection details in JSON format
synapse inspect <symbol> --json
```

### Context and Retrieval

```bash
# Generate focused context bundle for LLM prompts
synapse context <query>

# Limit number of retrieved symbols (default: 10)
synapse context <query> --max-results 5

# Cap total byte size of generated context (default: 32768)
synapse context <query> --max-bytes 16384

# Control graph traversal depth for context expansion (default: 1)
synapse context <query> --depth 2

# Write generated context to a specified file
synapse context <query> -o context.txt

# Emit context structure as JSON
synapse context <query> --json
```

### Data Export

```bash
# Export full repository knowledge graph to JSON
synapse export json -o index.json

# Export structured Markdown representation
synapse export md -o index.md

# Package JSON, Markdown, and README into a ZIP bundle
synapse export zip -o index.zip
```

## Command Options Matrix

| Command | Option | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `index` | `--rebuild` | Flag | `false` | Drop existing database and index all files anew. |
| `index` | `--json` | Flag | `false` | Emit summary metrics as JSON. |
| `status` | `--json` | Flag | `false` | Emit status information as JSON. |
| `search` | `--limit` | Integer | `20` | Maximum number of results to display. |
| `search` | `--json` | Flag | `false` | Output results in JSON format. |
| `inspect` | `--depth` | Integer | `1` | Traversal depth for inbound/outbound references. |
| `inspect` | `--json` | Flag | `false` | Output symbol details in JSON format. |
| `context` | `--max-results` | Integer | `10` | Maximum symbol definitions to include. |
| `context` | `--max-bytes` | Integer | `32768` | Maximum output size in bytes. |
| `context` | `--depth` | Integer | `1` | Graph traversal expansion depth. |
| `context` | `-o`, `--output` | Path | `stdout` | Destination file path for generated context. |
| `context` | `--json` | Flag | `false` | Output context bundle in JSON format. |
| `export` | `<format>` | String | Required | Export format: `json`, `md`, or `zip`. |
| `export` | `-o`, `--output` | Path | Auto | Destination file path for exported artifact. |

## Exit Codes

| Code | Name | Condition |
| :--- | :--- | :--- |
| `0` | Success | Command finished without errors. |
| `1` | Operational Error | Missing repository, uninitialized database, file I/O failure, corrupt database. |
| `2` | Usage Error | Invalid syntax, missing required arguments, unrecognized options. |

## Default File System Paths

| Path | Purpose |
| :--- | :--- |
| `.synapse/` | Directory storing internal metadata and database. |
| `.synapse/index.db` | SQLite database storing symbols, references, and commit state. |
| `.synapseignore` | Optional file listing glob patterns to exclude from indexing. |
