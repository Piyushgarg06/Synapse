---
title: Exports
description: Detailed contents and structure of JSON, Markdown, and ZIP exports
---

# Exports

Synapse exports canonical index representations into three distinct portable formats.

---

## 1. JSON Export (`synapse export json`)

The JSON export provides a complete dump of the relational knowledge graph suitable for machine ingestion:

- **Root metadata**: `schema_version` (integer 1), `checkpoint` (full commit SHA).
- **Metric counts**: `files_count`, `symbols_count`, `edges_count`, `references_count`.
- **`files` array**: Object per tracked file with `path`, `language`, `has_errors`, `parse_error`.
- **`symbols` array**: Object per symbol declaration with deterministic 16-hex `id`, `name`, `qualified_name`, `kind`, `file_path`, and coordinates.
- **`edges` array**: Object per directed relation with `edge_type`, `source_id`, `target_id`.
- **`references` array**: Object per identifier reference with `name`, `status`, `context_qualified_name`, `file_path`.

---

## 2. Markdown Export (`synapse export md`)

The Markdown export formats the index as human-readable reference documentation:

- **Header Section**: Lists the commit checkpoint and summary metrics.
- **Indexed Files Table**: Lists path, language, and error status for each file.
- **Symbols Table**: Lists symbol name, qualified name, kind, file path, and start/end line bounds.
- **References Table**: Lists reference name, resolution status (`resolved` or `unresolved`), enclosing context, and file path.

---

## 3. ZIP Snapshot (`synapse export zip`)

The ZIP export produces a self-contained, portable archive containing three files:

```
snapshot.zip
  ├── index.json     (Complete structured JSON export)
  ├── index.md       (Complete formatted Markdown overview)
  └── README.txt     (Archive metadata and checkpoint hash)
```

### Determinism Features
To ensure byte-for-byte reproducibility across runs at the same Git commit:
- All archive members use a fixed timestamp: `2026-01-01 00:00:00`.
- File contents are sorted before archiving.
- Deflate compression level is normalized.
- Two identical exports from the same commit produce matching SHA-256 archive checksums.
