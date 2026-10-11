"""Structural retrieval and context generation engine for Synapse."""

from __future__ import annotations

import os
from typing import Optional

from synapse.index.store import IndexDB
from synapse.git.ops import is_working_tree_dirty


def search_symbols_and_files(db: IndexDB, query: str, limit: int = 20) -> list[dict]:
    """Search for symbols and files by name with deterministic ranking.
    
    Ranking:
    1. Exact symbol name match
    2. Exact file path match
    3. Prefix symbol name match
    4. Prefix file path match
    5. Substring match
    Tie-breakers: file_path, qualified_name.
    """
    results: list[dict] = []

    # 1. Search symbols
    sym_rows = db.conn.execute(
        """SELECT id, name, qualified_name, kind, file_path,
                  start_line, end_line
           FROM symbols
           WHERE name LIKE ? OR qualified_name LIKE ?
           ORDER BY
               CASE
                   WHEN name = ? THEN 0
                   WHEN qualified_name = ? THEN 1
                   WHEN name LIKE ? THEN 2
                   WHEN qualified_name LIKE ? THEN 3
                   ELSE 4
               END,
               file_path,
               qualified_name
           LIMIT ?""",
        (f"%{query}%", f"%{query}%", query, query, f"{query}%", f"{query}%", limit),
    ).fetchall()

    for r in sym_rows:
        results.append({
            "type": "symbol",
            "id": r["id"],
            "name": r["name"],
            "qualified_name": r["qualified_name"],
            "kind": r["kind"],
            "file_path": r["file_path"],
            "start_line": r["start_line"],
            "end_line": r["end_line"],
        })

    # 2. Search files if limit not reached
    remaining = limit - len(results)
    if remaining > 0:
        file_rows = db.conn.execute(
            """SELECT path, language
               FROM files
               WHERE path LIKE ?
               ORDER BY
                   CASE
                       WHEN path = ? THEN 0
                       WHEN path LIKE ? THEN 1
                       ELSE 2
                   END,
                   path
               LIMIT ?""",
            (f"%{query}%", query, f"{query}%", remaining),
        ).fetchall()

        for r in file_rows:
            results.append({
                "type": "file",
                "id": f"file:{r['path']}",
                "name": os.path.basename(r["path"]),
                "qualified_name": r["path"],
                "kind": "file",
                "file_path": r["path"],
                "start_line": 1,
                "end_line": 1,
            })

    return results[:limit]


def inspect_symbol(db: IndexDB, symbol_query: str, depth: int = 1) -> dict:
    """Inspect a symbol's definition, location, and relationships up to depth."""
    # Find matching symbols
    matches = db.conn.execute(
        """SELECT id, name, qualified_name, kind, file_path,
                  start_byte, end_byte, start_line, start_column,
                  end_line, end_column, ordinal
           FROM symbols
           WHERE name = ? OR qualified_name = ?
           ORDER BY file_path, qualified_name""",
        (symbol_query, symbol_query),
    ).fetchall()

    if not matches:
        # Fallback to substring match
        matches = db.conn.execute(
            """SELECT id, name, qualified_name, kind, file_path,
                      start_byte, end_byte, start_line, start_column,
                      end_line, end_column, ordinal
               FROM symbols
               WHERE name LIKE ? OR qualified_name LIKE ?
               ORDER BY file_path, qualified_name""",
            (f"%{symbol_query}%", f"%{symbol_query}%"),
        ).fetchall()

    if not matches:
        return {"found": False, "message": f"Symbol '{symbol_query}' not found."}

    if len(matches) > 1:
        # Ambiguous: list candidates
        candidates = [
            {
                "id": m["id"],
                "name": m["name"],
                "qualified_name": m["qualified_name"],
                "kind": m["kind"],
                "file_path": m["file_path"],
                "line": m["start_line"],
            }
            for m in matches
        ]
        return {
            "found": True,
            "ambiguous": True,
            "query": symbol_query,
            "message": f"Ambiguous symbol query '{symbol_query}'. Multiple symbols match:",
            "candidates": candidates,
        }

    # Exactly one symbol found
    sym = dict(matches[0])
    symbol_id = sym["id"]

    # Containing file and symbol
    parent_qname = sym["qualified_name"].rsplit(".", 1)[0] if "." in sym["qualified_name"] else None
    parent_sym = None
    if parent_qname:
        parent_row = db.conn.execute(
            "SELECT id, name, qualified_name, kind FROM symbols WHERE file_path = ? AND qualified_name = ?",
            (sym["file_path"], parent_qname),
        ).fetchone()
        if parent_row:
            parent_sym = dict(parent_row)

    # Resolved callers and callees (with depth traversal)
    callers = _traverse_relationships(db, symbol_id, "CALLS", direction="incoming", max_depth=depth)
    callees = _traverse_relationships(db, symbol_id, "CALLS", direction="outgoing", max_depth=depth)

    # Inheritance
    bases = _traverse_relationships(db, symbol_id, "INHERITS_FROM", direction="outgoing", max_depth=depth)
    subclasses = _traverse_relationships(db, symbol_id, "INHERITS_FROM", direction="incoming", max_depth=depth)

    # File imports
    import_rows = db.conn.execute(
        "SELECT module_name, imported_names, alias FROM imports WHERE file_path = ?",
        (sym["file_path"],),
    ).fetchall()
    imports = [dict(r) for r in import_rows]

    # Unresolved references in this symbol's context
    unresolved_rows = db.conn.execute(
        """SELECT name, start_line
           FROM references_
           WHERE file_path = ? AND context_qualified_name = ? AND status = 'unresolved'""",
        (sym["file_path"], sym["qualified_name"]),
    ).fetchall()
    unresolved_refs = [dict(r) for r in unresolved_rows]

    return {
        "found": True,
        "ambiguous": False,
        "symbol": sym,
        "parent": parent_sym,
        "callers": callers,
        "callees": callees,
        "base_classes": bases,
        "subclasses": subclasses,
        "file_imports": imports,
        "unresolved_references": unresolved_refs,
        "depth": depth,
    }


def _traverse_relationships(
    db: IndexDB,
    start_id: str,
    edge_type: str,
    direction: str = "outgoing",
    max_depth: int = 1,
) -> list[dict]:
    """Traverse relationships (e.g. CALLS, INHERITS_FROM) up to max_depth."""
    visited: set[str] = set()
    queue = [(start_id, 0)]
    results: list[dict] = []

    while queue:
        curr_id, curr_depth = queue.pop(0)
        if curr_depth >= max_depth:
            continue

        if direction == "outgoing":
            rows = db.conn.execute(
                """SELECT e.target_id as rel_id, s.name, s.qualified_name, s.kind, s.file_path, s.start_line
                   FROM edges e
                   JOIN symbols s ON e.target_id = s.id
                   WHERE e.edge_type = ? AND e.source_id = ?""",
                (edge_type, curr_id),
            ).fetchall()
        else:
            rows = db.conn.execute(
                """SELECT e.source_id as rel_id, s.name, s.qualified_name, s.kind, s.file_path, s.start_line
                   FROM edges e
                   JOIN symbols s ON e.source_id = s.id
                   WHERE e.edge_type = ? AND e.target_id = ?""",
                (edge_type, curr_id),
            ).fetchall()

        for r in rows:
            target_id = r["rel_id"]
            if target_id not in visited and target_id != start_id:
                visited.add(target_id)
                res = dict(r)
                res["depth"] = curr_depth + 1
                results.append(res)
                queue.append((target_id, curr_depth + 1))

    return results


def generate_context(
    db: IndexDB,
    repo_root: str,
    query: str,
    max_results: int = 10,
    max_bytes: int = 8192,
    depth: int = 2,
) -> dict:
    """Generate structured context document for an external LLM / coding agent."""
    # 1. Search for primary seed symbols/files
    matches = search_symbols_and_files(db, query, limit=max_results)
    
    included_items: list[dict] = []
    seen_ids: set[str] = set()

    for item in matches:
        if item["id"] in seen_ids:
            continue
        seen_ids.add(item["id"])

        reason = "exact match" if item["name"] == query or item["qualified_name"] == query else f"search match for '{query}'"
        snippet, is_stale, was_truncated = _read_source_snippet(
            repo_root, item["file_path"], item["start_line"], item["end_line"], max_bytes
        )

        item_data = {
            "id": item["id"],
            "name": item["name"],
            "qualified_name": item["qualified_name"],
            "kind": item["kind"],
            "file_path": item["file_path"],
            "start_line": item["start_line"],
            "end_line": item["end_line"],
            "reason": reason,
            "snippet": snippet,
            "is_stale": is_stale,
            "was_truncated": was_truncated,
        }

        # Traversal for symbol relationships up to depth
        if item["type"] == "symbol" and depth > 1:
            callers = _traverse_relationships(db, item["id"], "CALLS", "incoming", max_depth=depth - 1)
            callees = _traverse_relationships(db, item["id"], "CALLS", "outgoing", max_depth=depth - 1)
            item_data["callers"] = callers
            item_data["callees"] = callees

        included_items.append(item_data)
        if len(included_items) >= max_results:
            break

    # Check unresolved references for included items
    unresolved_summary: list[dict] = []
    for it in included_items:
        if it["kind"] != "file":
            unres = db.conn.execute(
                "SELECT name, start_line FROM references_ WHERE file_path = ? AND context_qualified_name = ? AND status = 'unresolved'",
                (it["file_path"], it["qualified_name"]),
            ).fetchall()
            for u in unres:
                unresolved_summary.append({
                    "symbol": it["qualified_name"],
                    "file_path": it["file_path"],
                    "reference": u["name"],
                    "line": u["start_line"],
                })

    return {
        "query": query,
        "max_results": max_results,
        "max_bytes": max_bytes,
        "depth": depth,
        "results_count": len(included_items),
        "items": included_items,
        "unresolved_dependencies": unresolved_summary,
        "disclaimer": (
            "Note: This context document was generated deterministically from static analysis. "
            "Snippets reflect indexed files. Dynamic calls, runtime reflection, and unindexed files "
            "remain unresolved and must not be assumed to be fully understood."
        ),
    }


def _read_source_snippet(
    repo_root: str,
    file_path: str,
    start_line: int,
    end_line: int,
    max_bytes: int,
) -> tuple[str, bool, bool]:
    """Read actual source lines from file, check if stale, and enforce byte limit."""
    abs_path = os.path.join(repo_root, file_path.replace("/", os.sep))
    if not os.path.isfile(abs_path):
        return ("[File not found on disk]", True, False)

    # Check if working tree has changes for this file (stale check)
    is_stale = False
    try:
        from synapse.git.ops import _run_git
        diff = _run_git(["diff", "HEAD", "--", file_path], repo_root).strip()
        if diff:
            is_stale = True
    except Exception:
        pass

    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        return (f"[Error reading file: {e}]", is_stale, False)

    # Extract lines 1-based inclusive
    snippet_lines = lines[max(0, start_line - 1):end_line]
    raw_text = "".join(snippet_lines)

    # Byte bounding
    encoded = raw_text.encode("utf-8")
    was_truncated = False
    if len(encoded) > max_bytes:
        raw_text = encoded[:max_bytes].decode("utf-8", errors="replace") + "\n... [Snippet truncated]"
        was_truncated = True

    return (raw_text, is_stale, was_truncated)
