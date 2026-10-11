"""Deterministic index exporter for Synapse (JSON, Markdown, ZIP)."""

from __future__ import annotations

import io
import json
import os
import zipfile
from typing import Optional

from synapse.index.store import IndexDB, SCHEMA_VERSION


def export_json(db: IndexDB, repo_root: str = "") -> dict:
    """Generate structured, schema-versioned JSON export of the index."""
    dump = db.get_normalized_dump()
    checkpoint = db.get_checkpoint()
    
    return {
        "schema_version": SCHEMA_VERSION,
        "checkpoint": checkpoint,
        "files_count": len(dump["files"]),
        "symbols_count": len(dump["symbols"]),
        "edges_count": len(dump["edges"]),
        "references_count": len(dump["references"]),
        "files": dump["files"],
        "symbols": dump["symbols"],
        "edges": dump["edges"],
        "references": dump["references"],
    }


def export_markdown(db: IndexDB) -> str:
    """Generate a deterministic, human-readable Markdown export from the index."""
    dump = db.get_normalized_dump()
    checkpoint = db.get_checkpoint() or "(not indexed)"
    
    lines = [
        "# Synapse Repository Index",
        "",
        f"- **Checkpoint**: `{checkpoint}`",
        f"- **Files**: {len(dump['files'])}",
        f"- **Symbols**: {len(dump['symbols'])}",
        f"- **Edges**: {len(dump['edges'])}",
        f"- **References**: {len(dump['references'])}",
        "",
        "## Indexed Files",
        "",
        "| File Path | Language | Has Errors |",
        "| --- | --- | --- |",
    ]
    
    for f in dump["files"]:
        err = "Yes" if f.get("has_errors") or f.get("parse_error") else "No"
        lines.append(f"| `{f['path']}` | {f['language']} | {err} |")
    
    lines.extend([
        "",
        "## Symbols",
        "",
        "| Name | Qualified Name | Kind | File | Lines |",
        "| --- | --- | --- | --- | --- |",
    ])
    
    for s in dump["symbols"]:
        lines.append(
            f"| `{s['name']}` | `{s['qualified_name']}` | {s['kind']} | `{s['file_path']}` | {s['start_line']}-{s['end_line']} |"
        )
    
    lines.extend([
        "",
        "## Graph Relationships",
        "",
        "| Type | Source | Target |",
        "| --- | --- | --- |",
    ])
    
    for e in dump["edges"]:
        lines.append(f"| `{e['edge_type']}` | `{e['source_id']}` | `{e['target_id']}` |")
    
    lines.extend([
        "",
        "## References",
        "",
        "| Name | Status | Context | File |",
        "| --- | --- | --- | --- |",
    ])
    
    for r in dump["references"]:
        ctx = r.get("context_qualified_name") or "(top-level)"
        lines.append(f"| `{r['name']}` | `{r['status']}` | `{ctx}` | `{r['file_path']}` |")
    
    lines.append("")
    return "\n".join(lines)


def export_zip(db: IndexDB, output_path: str, repo_root: str = ""):
    """Generate a valid, deterministic ZIP archive snapshot."""
    json_data = export_json(db, repo_root)
    json_bytes = json.dumps(json_data, indent=2, sort_keys=True).encode("utf-8")
    
    md_text = export_markdown(db)
    md_bytes = md_text.encode("utf-8")
    
    readme_text = (
        "Synapse Repository Intelligence Snapshot\n"
        "========================================\n\n"
        "Contents:\n"
        "- index.json: Structured index representation with schema version, symbols, and edges.\n"
        "- index.md: Human-readable markdown overview of repository structure.\n"
        "- README.txt: Archive metadata.\n\n"
        f"Generated from checkpoint: {db.get_checkpoint() or 'unknown'}\n"
    )
    readme_bytes = readme_text.encode("utf-8")
    
    # Deterministic timestamp for zip entries: 2026-01-01 00:00:00
    fixed_dt = (2026, 1, 1, 0, 0, 0)
    
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. index.json
        zi_json = zipfile.ZipInfo("index.json", fixed_dt)
        zf.writestr(zi_json, json_bytes)
        
        # 2. index.md
        zi_md = zipfile.ZipInfo("index.md", fixed_dt)
        zf.writestr(zi_md, md_bytes)
        
        # 3. README.txt
        zi_readme = zipfile.ZipInfo("README.txt", fixed_dt)
        zf.writestr(zi_readme, readme_bytes)
