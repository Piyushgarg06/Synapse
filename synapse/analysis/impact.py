"""Deletion impact analysis for Synapse.

Computes the blast radius of deleting a file or a specific symbol,
tracing every dependent through imports, call edges, inheritance,
and resolved references.
"""

from __future__ import annotations

import os
from typing import Optional

from synapse.index.store import IndexDB
from synapse.models import EdgeType


def analyze_file_deletion(db: IndexDB, file_path: str) -> dict:
    """Compute the blast radius of deleting a file.

    Returns a dict with:
      - found: whether the file exists in the index
      - ambiguous: True if multiple files match a partial path
      - file_path: normalised path
      - symbols_lost: symbols defined in the file
      - dependents: dict mapping relationship type to lists of affected items
      - summary: human-readable summary
    """
    posix_path = file_path.replace("\\", "/")

    # Check the file exists in the index (exact match first)
    file_row = db.conn.execute(
        "SELECT id, path, language FROM files WHERE path = ?",
        (posix_path,),
    ).fetchone()

    if not file_row:
        # Try matching suffix like '%/posix_path' or '%/posix_path.%'
        candidates = db.conn.execute(
            """SELECT id, path, language FROM files 
               WHERE path = ? OR path LIKE ? OR path LIKE ? OR path LIKE ?""",
            (posix_path, f"%/{posix_path}", f"%/{posix_path}.%", f"{posix_path}.%"),
        ).fetchall()
        if len(candidates) == 1:
            file_row = candidates[0]
            posix_path = file_row["path"]
        elif len(candidates) > 1:
            return {
                "found": True,
                "ambiguous": True,
                "file_path": posix_path,
                "candidates": [dict(c) for c in candidates],
            }
        else:
            return {"found": False, "file_path": posix_path}

    file_id = file_row["id"]

    # 1. Symbols defined in this file (these would be lost)
    symbols_lost = db.conn.execute(
        """SELECT id, name, qualified_name, kind, start_line, end_line
           FROM symbols WHERE file_path = ?
           ORDER BY start_line""",
        (posix_path,),
    ).fetchall()
    symbols_lost = [dict(r) for r in symbols_lost]
    symbol_ids = {s["id"] for s in symbols_lost}

    # 2. Files that import from this file's module
    # Check both EdgeType.IMPORTS edges and imports table
    importers_dict: dict[str, dict] = {}
    
    # Via edges:
    edge_importers = db.conn.execute(
        """SELECT DISTINCT file_path FROM edges
           WHERE edge_type = ? AND target_id = ? AND file_path != ?""",
        (EdgeType.IMPORTS.value, f"file:{posix_path}", posix_path),
    ).fetchall()
    for row in edge_importers:
        importers_dict[row["file_path"]] = {
            "file_path": row["file_path"],
            "module_name": posix_path,
            "imported_names": "",
            "start_line": 1,
        }

    # Via imports table:
    mod_pattern = _file_path_to_module_pattern(posix_path)
    file_base = os.path.basename(posix_path).rsplit(".", 1)[0]
    import_rows = db.conn.execute(
        """SELECT DISTINCT i.file_path, i.module_name, i.imported_names, i.start_line
           FROM imports i
           WHERE (i.module_name LIKE ? OR i.module_name LIKE ?) AND i.file_path != ?
           ORDER BY i.file_path, i.start_line""",
        (mod_pattern, f"%{file_base}%", posix_path),
    ).fetchall()
    for r in import_rows:
        importers_dict[r["file_path"]] = dict(r)

    importers = sorted(importers_dict.values(), key=lambda x: (x["file_path"], x.get("start_line", 1)))

    # 3. Callers of any symbol defined in this file (via resolved edges)
    callers = []
    for sym in symbols_lost:
        caller_rows = db.conn.execute(
            """SELECT DISTINCT s.name, s.qualified_name, s.kind,
                      s.file_path, s.start_line
               FROM edges e
               JOIN symbols s ON e.source_id = s.id
               WHERE e.edge_type = 'CALLS' AND e.target_id = ?""",
            (sym["id"],),
        ).fetchall()
        for c in caller_rows:
            if c["file_path"] != posix_path:  # skip self-calls within the file
                callers.append({
                    **dict(c),
                    "calls_symbol": sym["qualified_name"],
                })

    # 4. Subclasses of classes defined in this file
    subclasses = []
    for sym in symbols_lost:
        if sym["kind"] in ("class", "interface"):
            sub_rows = db.conn.execute(
                """SELECT DISTINCT s.name, s.qualified_name, s.kind,
                          s.file_path, s.start_line
                   FROM edges e
                   JOIN symbols s ON e.source_id = s.id
                   WHERE e.edge_type = 'INHERITS_FROM' AND e.target_id = ?""",
                (sym["id"],),
            ).fetchall()
            for s in sub_rows:
                if s["file_path"] != posix_path:
                    subclasses.append({
                        **dict(s),
                        "inherits_from": sym["qualified_name"],
                    })

    # 5. Resolved references pointing at symbols in this file
    ref_dependents = db.conn.execute(
        """SELECT DISTINCT r.file_path, r.name, r.context_qualified_name, r.start_line
           FROM references_ r
           WHERE r.status = 'resolved'
             AND r.resolved_symbol_id IN ({})
             AND r.file_path != ?
           ORDER BY r.file_path, r.start_line""".format(
            ",".join("?" for _ in symbol_ids)
        ),
        (*symbol_ids, posix_path),
    ).fetchall() if symbol_ids else []
    ref_dependents = [dict(r) for r in ref_dependents]

    # Collect all affected files
    affected_files: set[str] = set()
    for imp in importers:
        affected_files.add(imp["file_path"])
    for c in callers:
        affected_files.add(c["file_path"])
    for s in subclasses:
        affected_files.add(s["file_path"])
    for r in ref_dependents:
        affected_files.add(r["file_path"])

    return {
        "found": True,
        "file_path": posix_path,
        "language": file_row["language"],
        "symbols_lost": symbols_lost,
        "dependents": {
            "importers": importers,
            "callers": callers,
            "subclasses": subclasses,
            "references": ref_dependents,
        },
        "affected_files": sorted(affected_files),
        "affected_file_count": len(affected_files),
        "total_broken_links": len(importers) + len(callers) + len(subclasses) + len(ref_dependents),
    }


def analyze_symbol_deletion(db: IndexDB, symbol_query: str, file_path: Optional[str] = None) -> dict:
    """Compute the blast radius of deleting a specific symbol.

    Args:
        db: Open IndexDB instance.
        symbol_query: Symbol name or qualified name.
        file_path: Optional file path to scope the search to.

    Returns a dict with:
      - found: whether the symbol exists in the index
      - ambiguous: whether multiple matching symbols were found
      - symbol: the target symbol (if exactly 1 matched)
      - dependents: dict mapping relationship type to lists of affected items
    """
    posix_file = file_path.replace("\\", "/") if file_path else None

    # Step 1: Find matching symbols
    if posix_file:
        matches = db.conn.execute(
            """SELECT id, name, qualified_name, kind, file_path,
                      start_line, end_line
               FROM symbols
               WHERE (name = ? OR qualified_name = ?)
                 AND (file_path = ? OR file_path LIKE ? OR file_path LIKE ? OR file_path LIKE ?)
               ORDER BY file_path, qualified_name""",
            (symbol_query, symbol_query, posix_file, f"%/{posix_file}", f"%/{posix_file}.%", f"{posix_file}.%"),
        ).fetchall()

        if not matches:
            matches = db.conn.execute(
                """SELECT id, name, qualified_name, kind, file_path,
                          start_line, end_line
                   FROM symbols
                   WHERE (name LIKE ? OR qualified_name LIKE ?)
                     AND (file_path = ? OR file_path LIKE ? OR file_path LIKE ? OR file_path LIKE ?)
                   ORDER BY file_path, qualified_name""",
                (f"%{symbol_query}%", f"%{symbol_query}%", posix_file, f"%/{posix_file}", f"%/{posix_file}.%", f"{posix_file}.%"),
            ).fetchall()
    else:
        matches = db.conn.execute(
            """SELECT id, name, qualified_name, kind, file_path,
                      start_line, end_line
               FROM symbols
               WHERE name = ? OR qualified_name = ?
               ORDER BY file_path, qualified_name""",
            (symbol_query, symbol_query),
        ).fetchall()

        if not matches:
            matches = db.conn.execute(
                """SELECT id, name, qualified_name, kind, file_path,
                          start_line, end_line
                   FROM symbols
                   WHERE name LIKE ? OR qualified_name LIKE ?
                   ORDER BY file_path, qualified_name""",
                (f"%{symbol_query}%", f"%{symbol_query}%"),
            ).fetchall()

    if not matches:
        return {"found": False, "symbol_query": symbol_query, "file_path": posix_file}

    if len(matches) > 1:
        return {
            "found": True,
            "ambiguous": True,
            "symbol_query": symbol_query,
            "file_path": posix_file,
            "candidates": [dict(m) for m in matches],
        }

    sym = dict(matches[0])
    symbol_id = sym["id"]
    sym_file = sym["file_path"]

    # 1. Callers (who calls this symbol?)
    callers = db.conn.execute(
        """SELECT DISTINCT s.name, s.qualified_name, s.kind,
                  s.file_path, s.start_line
           FROM edges e
           JOIN symbols s ON e.source_id = s.id
           WHERE e.edge_type = 'CALLS' AND e.target_id = ?
           ORDER BY s.file_path, s.qualified_name""",
        (symbol_id,),
    ).fetchall()
    callers = [dict(r) for r in callers]

    # 2. Subclasses (who inherits from this?)
    subclasses = []
    if sym["kind"] in ("class", "interface"):
        sub_rows = db.conn.execute(
            """SELECT DISTINCT s.name, s.qualified_name, s.kind,
                      s.file_path, s.start_line
               FROM edges e
               JOIN symbols s ON e.source_id = s.id
               WHERE e.edge_type = 'INHERITS_FROM' AND e.target_id = ?
               ORDER BY s.file_path, s.qualified_name""",
            (symbol_id,),
        ).fetchall()
        subclasses = [dict(r) for r in sub_rows]

    # 3. Resolved references to this symbol from other files
    ref_dependents = db.conn.execute(
        """SELECT DISTINCT r.file_path, r.name, r.context_qualified_name, r.start_line
           FROM references_ r
           WHERE r.status = 'resolved' AND r.resolved_symbol_id = ?
           ORDER BY r.file_path, r.start_line""",
        (symbol_id,),
    ).fetchall()
    ref_dependents = [dict(r) for r in ref_dependents]

    # 4. Child symbols (contained within this symbol — they'd be lost too)
    children = db.conn.execute(
        """SELECT id, name, qualified_name, kind, start_line, end_line
           FROM symbols
           WHERE file_path = ? AND qualified_name LIKE ? AND id != ?
           ORDER BY start_line""",
        (sym_file, f"{sym['qualified_name']}.%", symbol_id),
    ).fetchall()
    children = [dict(r) for r in children]

    # Affected files
    affected_files: set[str] = set()
    for c in callers:
        affected_files.add(c["file_path"])
    for s in subclasses:
        affected_files.add(s["file_path"])
    for r in ref_dependents:
        affected_files.add(r["file_path"])

    return {
        "found": True,
        "ambiguous": False,
        "symbol": sym,
        "children_lost": children,
        "dependents": {
            "callers": callers,
            "subclasses": subclasses,
            "references": ref_dependents,
        },
        "affected_files": sorted(affected_files),
        "affected_file_count": len(affected_files),
        "total_broken_links": len(callers) + len(subclasses) + len(ref_dependents),
    }


def _file_path_to_module_pattern(file_path: str) -> str:
    """Convert a file path to a module import pattern for LIKE matching.

    e.g. 'synapse/core.py' -> '%synapse.core%'
         'synapse/index/store.py' -> '%synapse.index.store%'
    """
    # Strip extension
    if file_path.endswith(".py"):
        module = file_path[:-3]
    elif file_path.endswith(".js") or file_path.endswith(".ts"):
        module = file_path[:-3]
    elif file_path.endswith(".tsx") or file_path.endswith(".jsx"):
        module = file_path[:-4]
    else:
        module = file_path

    # Convert slashes to dots for Python-style module matching
    module = module.replace("/", ".")
    return f"%{module}%"
