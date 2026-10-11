"""Knowledge graph builder and reference resolution for Synapse."""

from __future__ import annotations

import os
import sqlite3
from typing import Optional

from synapse.models import EdgeType, ReferenceStatus


def build_graph_and_resolve(db, cursor: Optional[sqlite3.Cursor] = None):
    """Build knowledge graph nodes/edges and resolve references across the repository.
    
    Creates:
    - Repository CONTAINS File edges
    - File DEFINES top-level symbol edges
    - Class CONTAINS Method edges
    - File IMPORTS File edges
    - Function/Method CALLS Callee edges (for statically resolved calls)
    - Class INHERITS_FROM BaseClass edges (for statically resolved bases)
    - Symbol REFERENCES Target edges (for statically resolved references)
    
    Updates:
    - Reference resolution statuses to 'resolved' or 'unresolved'.
    """
    c = cursor or db.conn.cursor()

    # 1. Clear existing edges and re-initialize
    c.execute("DELETE FROM edges")

    # 2. Query all files and symbols
    c.execute("SELECT id, path, language FROM files")
    files_rows = c.fetchall()
    files = {row["path"]: dict(row) for row in files_rows}

    c.execute(
        """SELECT id, name, qualified_name, kind, file_id, file_path,
                  start_line, end_line, ordinal
           FROM symbols"""
    )
    symbol_rows = c.fetchall()
    all_symbols = [dict(row) for row in symbol_rows]

    # Organize symbols by file_path
    symbols_by_file: dict[str, list[dict]] = {}
    symbols_by_id: dict[str, dict] = {}
    for sym in all_symbols:
        symbols_by_file.setdefault(sym["file_path"], []).append(sym)
        symbols_by_id[sym["id"]] = sym

    # 3. Add Structural Containment & Definition Edges
    for file_path in files:
        # Repository CONTAINS File
        c.execute(
            """INSERT OR IGNORE INTO edges (edge_type, source_id, target_id, file_path)
               VALUES (?, ?, ?, ?)""",
            (EdgeType.CONTAINS.value, "repo:root", f"file:{file_path}", file_path),
        )

        file_syms = symbols_by_file.get(file_path, [])
        sym_qname_map = {s["qualified_name"]: s for s in file_syms}

        for sym in file_syms:
            qname = sym["qualified_name"]
            if "." in qname:
                parent_qname = qname.rsplit(".", 1)[0]
                parent_sym = sym_qname_map.get(parent_qname)
                if parent_sym:
                    # Class CONTAINS Method or Function CONTAINS nested Function
                    c.execute(
                        """INSERT OR IGNORE INTO edges (edge_type, source_id, target_id, file_path)
                           VALUES (?, ?, ?, ?)""",
                        (EdgeType.CONTAINS.value, parent_sym["id"], sym["id"], file_path),
                    )
                else:
                    # Fallback to File DEFINES
                    c.execute(
                        """INSERT OR IGNORE INTO edges (edge_type, source_id, target_id, file_path)
                           VALUES (?, ?, ?, ?)""",
                        (EdgeType.DEFINES.value, f"file:{file_path}", sym["id"], file_path),
                    )
            else:
                # Top-level symbol: File DEFINES Symbol
                c.execute(
                    """INSERT OR IGNORE INTO edges (edge_type, source_id, target_id, file_path)
                       VALUES (?, ?, ?, ?)""",
                    (EdgeType.DEFINES.value, f"file:{file_path}", sym["id"], file_path),
                )

    # 4. Resolve Imports across files
    # Build module resolution map
    # Python: module dotted path -> file_path
    py_module_map: dict[str, str] = {}
    for f_path in files:
        if f_path.endswith(".py"):
            mod = f_path[:-3].replace("/", ".")
            if mod.endswith(".__init__"):
                mod = mod[:-9]
            py_module_map[mod] = f_path

    c.execute(
        """SELECT id, file_id, file_path, module_name, imported_names,
                  alias, is_default, is_namespace
           FROM imports"""
    )
    import_rows = c.fetchall()

    # Track imported symbols per file: file_path -> {imported_name: target_symbol_id}
    imported_symbols_by_file: dict[str, dict[str, dict]] = {}

    for imp_row in import_rows:
        imp = dict(imp_row)
        source_file = imp["file_path"]
        mod_name = imp["module_name"]

        target_file = _resolve_module_file(mod_name, source_file, files, py_module_map)
        if target_file:
            # File IMPORTS File edge
            c.execute(
                """INSERT OR IGNORE INTO edges (edge_type, source_id, target_id, file_path)
                   VALUES (?, ?, ?, ?)""",
                (EdgeType.IMPORTS.value, f"file:{source_file}", f"file:{target_file}", source_file),
            )

            # Map imported names to target file symbols
            target_file_syms = symbols_by_file.get(target_file, [])
            target_sym_by_name = {s["name"]: s for s in target_file_syms}

            raw_names = imp["imported_names"].split(",") if imp["imported_names"] else []
            for name in raw_names:
                name = name.strip()
                if not name:
                    continue
                if name in target_sym_by_name:
                    imported_symbols_by_file.setdefault(source_file, {})[name] = target_sym_by_name[name]
                elif imp["alias"] and name == imp["alias"]:
                    imported_symbols_by_file.setdefault(source_file, {})[name] = target_sym_by_name.get(name)

    # 5. Resolve Inheritance
    c.execute("SELECT id, file_id, file_path, class_name, base_class_name FROM inheritance")
    inh_rows = c.fetchall()

    for inh_row in inh_rows:
        inh = dict(inh_row)
        file_path = inh["file_path"]
        class_name = inh["class_name"]
        base_name = inh["base_class_name"]

        file_syms = symbols_by_file.get(file_path, [])
        class_sym = next((s for s in file_syms if s["name"] == class_name and s["kind"] == "class"), None)
        if not class_sym:
            continue

        # Try resolving base class:
        base_sym = None
        # Same-file match
        base_sym = next((s for s in file_syms if s["name"] == base_name and s["kind"] == "class"), None)
        # Import-bound match
        if not base_sym:
            imported = imported_symbols_by_file.get(file_path, {})
            if base_name in imported and imported[base_name]["kind"] == "class":
                base_sym = imported[base_name]

        if base_sym:
            c.execute(
                """INSERT OR IGNORE INTO edges (edge_type, source_id, target_id, file_path)
                   VALUES (?, ?, ?, ?)""",
                (EdgeType.INHERITS_FROM.value, class_sym["id"], base_sym["id"], file_path),
            )

    # Build inheritance map per file: file_path -> {class_name: [base_class_names]}
    inheritance_by_file: dict[str, dict[str, list[str]]] = {}
    for inh_row in inh_rows:
        inh = dict(inh_row)
        inheritance_by_file.setdefault(inh["file_path"], {}).setdefault(inh["class_name"], []).append(inh["base_class_name"])

    # 6. Resolve Calls
    c.execute(
        """SELECT id, file_id, file_path, caller_qualified_name, callee_name
           FROM calls"""
    )
    call_rows = c.fetchall()

    for call_row in call_rows:
        call = dict(call_row)
        file_path = call["file_path"]
        caller_qname = call["caller_qualified_name"]
        callee_name = call["callee_name"]

        file_syms = symbols_by_file.get(file_path, [])
        caller_sym = next((s for s in file_syms if s["qualified_name"] == caller_qname), None)
        if not caller_sym:
            continue

        target_sym = _resolve_symbol_name(
            callee_name, caller_qname, file_path, file_syms,
            imported_symbols_by_file, inheritance_by_file, symbols_by_file,
        )
        if target_sym:
            c.execute(
                """INSERT OR IGNORE INTO edges (edge_type, source_id, target_id, file_path)
                   VALUES (?, ?, ?, ?)""",
                (EdgeType.CALLS.value, caller_sym["id"], target_sym["id"], file_path),
            )

    # 7. Resolve References
    c.execute(
        """SELECT id, file_id, file_path, name, context_qualified_name
           FROM references_"""
    )
    ref_rows = c.fetchall()

    for ref_row in ref_rows:
        ref = dict(ref_row)
        ref_id = ref["id"]
        file_path = ref["file_path"]
        name = ref["name"]
        context_qname = ref["context_qualified_name"]

        file_syms = symbols_by_file.get(file_path, [])
        target_sym = _resolve_symbol_name(
            name, context_qname, file_path, file_syms,
            imported_symbols_by_file, inheritance_by_file, symbols_by_file,
        )

        if target_sym:
            c.execute(
                """UPDATE references_
                   SET status = ?, resolved_symbol_id = ?
                   WHERE id = ?""",
                (ReferenceStatus.RESOLVED.value, target_sym["id"], ref_id),
            )
            context_sym = next((s for s in file_syms if s["qualified_name"] == context_qname), None)
            if context_sym:
                c.execute(
                    """INSERT OR IGNORE INTO edges (edge_type, source_id, target_id, file_path)
                       VALUES (?, ?, ?, ?)""",
                    (EdgeType.REFERENCES.value, context_sym["id"], target_sym["id"], file_path),
                )
        else:
            c.execute(
                """UPDATE references_
                   SET status = ?, resolved_symbol_id = NULL
                   WHERE id = ?""",
                (ReferenceStatus.UNRESOLVED.value, ref_id),
            )


def _resolve_symbol_name(
    callee_name: str,
    caller_qname: str,
    file_path: str,
    file_syms: list[dict],
    imported_symbols_by_file: dict[str, dict[str, dict]],
    inheritance_by_file: Optional[dict[str, dict[str, list[str]]]] = None,
    symbols_by_file: Optional[dict[str, list[dict]]] = None,
) -> Optional[dict]:
    """Resolve a callee/reference name to a known symbol."""
    # 1. Direct match in same file by simple name
    direct = [s for s in file_syms if s["name"] == callee_name]
    if len(direct) == 1:
        return direct[0]

    # 2. Check imported symbols for this file by simple name
    imported = imported_symbols_by_file.get(file_path, {})
    if callee_name in imported and imported[callee_name]:
        return imported[callee_name]

    # 3. Check if it's this.method or self.method inside a class method
    if (callee_name.startswith("this.") or callee_name.startswith("self.")) and "." in caller_qname:
        method_name = callee_name.split(".", 1)[1]
        class_name = caller_qname.rsplit(".", 1)[0]
        
        # Check current class methods
        target_qname = f"{class_name}.{method_name}"
        match = next((s for s in file_syms if s["qualified_name"] == target_qname), None)
        if match:
            return match
        
        # Check inherited base classes
        if inheritance_by_file and symbols_by_file:
            base_classes = inheritance_by_file.get(file_path, {}).get(class_name, [])
            for base_name in base_classes:
                base_sym = next((s for s in file_syms if s["name"] == base_name and s["kind"] == "class"), None)
                if not base_sym:
                    base_sym = imported.get(base_name)
                if base_sym:
                    base_file = base_sym["file_path"]
                    base_syms = symbols_by_file.get(base_file, [])
                    base_method_qname = f"{base_sym['qualified_name']}.{method_name}"
                    match = next((s for s in base_syms if s["qualified_name"] == base_method_qname), None)
                    if match:
                        return match

    # 4. Dot member lookup (e.g. Config.load or BaseService.execute)
    if "." in callee_name and symbols_by_file:
        obj_name, member_name = callee_name.split(".", 1)
        obj_sym = imported.get(obj_name) or next((s for s in file_syms if s["name"] == obj_name), None)
        if obj_sym:
            obj_file = obj_sym["file_path"]
            obj_file_syms = symbols_by_file.get(obj_file, [])
            target_qname = f"{obj_sym['qualified_name']}.{member_name}"
            match = next((s for s in obj_file_syms if s["qualified_name"] == target_qname), None)
            if match:
                return match

    return None


def _resolve_module_file(
    module_name: str,
    source_file: str,
    all_files: dict[str, dict],
    py_module_map: dict[str, str],
) -> Optional[str]:
    """Resolve an imported module string to a repository file path."""
    source_dir = os.path.dirname(source_file)

    # 1. Relative import (starts with .)
    if module_name.startswith("."):
        # JS/TS relative import: e.g. './lib', '../utils'
        # Python relative import: e.g. '.local', '..types'
        if module_name.startswith("./") or module_name.startswith("../"):
            # JS/TS path resolution
            rel_path = os.path.normpath(os.path.join(source_dir, module_name)).replace("\\", "/")
            # Try exact match
            if rel_path in all_files:
                return rel_path
            # Try extensions
            for ext in (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"):
                candidate = rel_path + ext
                if candidate in all_files:
                    return candidate
            # Try index file
            for ext in (".js", ".ts", ".jsx", ".tsx"):
                candidate = f"{rel_path}/index{ext}"
                if candidate in all_files:
                    return candidate
        else:
            # Python relative import: count leading dots
            dots = len(module_name) - len(module_name.lstrip("."))
            rest = module_name[dots:]
            cur_dir = source_dir
            for _ in range(dots - 1):
                cur_dir = os.path.dirname(cur_dir)
            target_mod = (f"{cur_dir}/{rest}" if cur_dir else rest).replace("\\", "/").replace("/", ".")
            if target_mod.endswith("."):
                target_mod = target_mod[:-1]
            if target_mod in py_module_map:
                return py_module_map[target_mod]

    # 2. Python absolute module import
    if module_name in py_module_map:
        return py_module_map[module_name]

    # Check suffix match for nested modules (e.g. 'foo.bar' matching 'src/foo/bar.py')
    for mod, f_path in py_module_map.items():
        if mod == module_name or mod.endswith(f".{module_name}"):
            return f_path

    return None
