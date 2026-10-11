---
title: Determinism
description: Reproducible identifiers, stable ordering, and identical export artifacts
---

# Determinism

Synapse produces reproducible outputs across repeated runs, different environments, and separate operating systems.

---

## Areas of Deterministic Behavior

### 1. Stable Symbol Identifiers
Symbol identifiers do not rely on auto-incrementing database primary keys or random UUIDs. They are computed using a SHA-256 hash of normalized components:

```
file_path + ":" + qualified_name + ":" + kind + ":" + ordinal
```

Because file paths use forward slashes on all platforms, the same symbol yields the identical 16-hex identifier on Windows, macOS, and Linux.

### 2. Deterministic Query Ordering
All retrieval queries specify explicit secondary and tertiary sort orders in SQL:
- Symbols: `ORDER BY file_path, qualified_name, kind, ordinal`
- Edges: `ORDER BY edge_type, source_id, target_id`
- Files: `ORDER BY path`

This prevents non-deterministic row iteration differences caused by underlying SQLite query planner decisions.

### 3. Bit-for-Bit Deterministic ZIP Exports
Standard ZIP archives vary on every build because filesystems record the current system timestamp for each archive member.

Synapse forces a fixed timestamp tuple `(2026, 1, 1, 0, 0, 0)` for all members inside `synapse export zip`:

```python
fixed_dt = (2026, 1, 1, 0, 0, 0)
zi = zipfile.ZipInfo("index.json", fixed_dt)
zf.writestr(zi, json_bytes)
```

Exporting a ZIP archive twice at the same commit produces byte-identical files with matching SHA-256 checksums.

---

## How to Verify Determinism

You can verify output reproducibility in your terminal:

```bash
# Export the JSON index twice
synapse export json -o run1.json
synapse export json -o run2.json

# Compare file checksums
git hash-object run1.json run2.json
```

Both hash commands return identical git object hashes.

---

## Related Reference

- To learn about export formats, see [Exports Reference](/reference/exports).
- To inspect symbol ID construction, see [Symbols and Identifiers](/concepts/symbols-and-ids).
