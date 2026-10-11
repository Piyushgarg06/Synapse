---
title: synapse export
description: Reference documentation for the synapse export command
---

# synapse export

Exports canonical index data into JSON, Markdown, or a deterministic ZIP snapshot.

---

## Synopsis

```
synapse export [-h] [-o OUTPUT] {json,md,zip}
```

---

## Description

`synapse export` dumps the persistent structural representation into self-contained files.
- `json`: Full schema-versioned JSON dump containing files, symbols, references, and edges.
- `md`: Markdown document with tables of indexed files, symbols, and references.
- `zip`: Self-contained archive package containing `index.json`, `index.md`, and `README.txt`.

- **Reads**: `.synapse/index.db`.
- **Writes**: Output path specified by `-o` or `--output`. For `zip`, defaults to `synapse_export.zip` in repository root if `-o` is omitted. For `json` and `md`, prints to stdout if `-o` is omitted.
- **Never touches**: User source files.

---

## Options and Arguments

| Argument / Option | Type | Default | Description |
|---|---|---|---|
| `format` | Positional String | Required (`json`, `md`, `zip`) | Export target format |
| `-o`, `--output` | String | `None` | Output file path |
| `-h`, `--help` | Flag | N/A | Show help message and exit |

---

## Output

### Export to File
```bash
$ synapse export json -o index.json
Exported JSON index to index.json

$ synapse export md -o index.md
Exported Markdown overview to index.md

$ synapse export zip -o snapshot.zip
Exported ZIP snapshot to snapshot.zip
```

### Export to Terminal (`stdout`)
When `-o` is omitted for `json` or `md`, raw content is printed to stdout so it can be redirected:

```bash
synapse export json > custom_index.json
```

---

## Exit Codes

| Code | Condition |
|---|---|
| `0` | Export completed successfully |
| `1` | Operational error (Synapse not initialized, unknown format, or write error) |
| `2` | Missing format argument or invalid option |

---

## Errors and Diagnostics

### Unknown export format
```
Error: Unknown export format 'html'
```
- **Cause**: Specified format is not in `json`, `md`, `zip`.
- **Fix**: Choose one of the three supported formats.

---

## Examples

### Example 1: Export ZIP snapshot
```bash
$ synapse export zip -o snapshot.zip
Exported ZIP snapshot to snapshot.zip
```

### Example 2: Stream Markdown overview
```bash
$ synapse export md -o architecture.md
Exported Markdown overview to architecture.md
```
