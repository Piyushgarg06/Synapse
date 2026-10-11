---
title: Exporting Data
description: How to export repository index data to JSON, Markdown, and ZIP archives
---

# Exporting Data

Goal: Export the structural index and knowledge graph into portable JSON, Markdown, or ZIP archive formats.

---

## Prerequisites

- An initialized and indexed repository.

---

## Steps

### Step 1: Export structured JSON
To export the complete index with symbols, edges, and references in machine-readable JSON:

```bash
synapse export json -o index.json
```

Output:

```
Exported JSON index to index.json
```

The resulting file contains the full schema-versioned graph ready for ingestion by analysis scripts or external tools.

### Step 2: Export human-readable Markdown
To generate an architectural reference document in Markdown:

```bash
synapse export md -o index.md
```

Output:

```
Exported Markdown overview to index.md
```

The generated file contains formatted tables of all indexed files, symbols, and references.

### Step 3: Export a deterministic ZIP snapshot
To create a self-contained archive package:

```bash
synapse export zip -o snapshot.zip
```

Output:

```
Exported ZIP snapshot to snapshot.zip
```

---

## How to Confirm It Worked

Verify the contents of the generated ZIP archive using your system unzip utility:

```bash
unzip -l snapshot.zip
```

Output:

```
Archive:  snapshot.zip
  Length      Date    Time    Name
---------  ---------- -----   ----
     7893  2026-01-01 00:00   index.json
     3639  2026-01-01 00:00   index.md
      351  2026-01-01 00:00   README.txt
---------                     -------
    11883                     3 files
```

The archive contains `index.json`, `index.md`, and `README.txt` with normalized `2026-01-01 00:00` timestamps.

---

## Related Guides

- For complete export schemas and structure, see [Exports Reference](/reference/exports).
- For JSON field-by-field specifications, see [JSON Output Specifications](/reference/json-output).
