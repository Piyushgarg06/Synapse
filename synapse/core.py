"""Core indexing engine for Synapse."""

from __future__ import annotations

import os
import sys
from typing import Optional

from synapse.git.ops import (
    find_repo_root, get_head_commit, get_all_tracked_files,
    get_changed_files, is_working_tree_dirty, is_ancestor,
    get_tracked_files_at_commit, get_working_tree_files,
    get_working_tree_status, GitError,
)
from synapse.analysis.dispatcher import analyze_file
from synapse.parsing.parser import get_language_for_file
from synapse.index.store import IndexDB
from synapse.graph.builder import build_graph_and_resolve
from synapse.exclusions import should_exclude_path


SYNAPSE_DIR = ".synapse"
DB_NAME = "index.db"


def get_db_path(repo_root: str) -> str:
    """Get the path to the index database."""
    return os.path.join(repo_root, SYNAPSE_DIR, DB_NAME)


def init_synapse(repo_root: str) -> tuple[bool, str]:
    """Initialize Synapse in a repository.
    
    Returns (success, message).
    Safe to call repeatedly — does not overwrite existing data.
    """
    synapse_dir = os.path.join(repo_root, SYNAPSE_DIR)
    db_path = get_db_path(repo_root)
    
    if os.path.exists(db_path):
        # Verify we can open it
        try:
            with IndexDB(db_path) as db:
                version = db.get_state("schema_version")
                return True, f"Synapse already initialized (schema v{version}). Existing data preserved."
        except Exception as e:
            return False, f"Synapse directory exists but database is corrupt: {e}"
    
    os.makedirs(synapse_dir, exist_ok=True)
    gitignore_path = os.path.join(synapse_dir, ".gitignore")
    if not os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, "w") as f:
                f.write("*\n")
        except OSError:
            pass
    
    try:
        with IndexDB(db_path) as db:
            version = db.get_state("schema_version")
            return True, f"Synapse initialized successfully (schema v{version})."
    except Exception as e:
        return False, f"Failed to initialize Synapse: {e}"


def run_index(repo_root: str, rebuild: bool = False, working_tree: bool = False) -> tuple[bool, dict]:
    """Run the indexing process.
    
    Args:
        repo_root: Absolute path to the repository root.
        rebuild: Force a full rebuild of the index.
        working_tree: Index the working tree (including uncommitted and untracked files).
    
    Returns (success, stats_dict).
    """
    db_path = get_db_path(repo_root)
    
    if not os.path.exists(db_path):
        return False, {"error": "Synapse not initialized. Run 'synapse init' first."}
    
    with IndexDB(db_path) as db:
        if working_tree:
            return _working_tree_index(db, repo_root, is_rebuild=rebuild)

        head = get_head_commit(repo_root)
        if head is None:
            return True, {
                "message": "Empty repository (no commits). Nothing to index.",
                "files_processed": 0,
                "symbols_found": 0,
            }
        
        checkpoint = db.get_checkpoint()
        
        if rebuild or checkpoint is None:
            return _full_index(db, repo_root, head, is_rebuild=rebuild)
        
        if checkpoint == head:
            # If working tree was clean, ensure working_tree_indexed flag is cleared
            if not is_working_tree_dirty(repo_root) and db.get_state("working_tree_indexed") == "1":
                db.conn.execute("DELETE FROM state WHERE key = 'working_tree_indexed'")
                db.conn.commit()

            msg = "Index is up to date. Nothing to do."
            if is_working_tree_dirty(repo_root):
                msg = "Index is up to date with HEAD. Working tree has uncommitted changes (use 'synapse index --working-tree' to index them)."

            return True, {
                "message": msg,
                "files_processed": 0,
                "symbols_found": db.get_symbol_count(),
                "checkpoint": checkpoint,
                "reparsed": 0,
            }
        
        # Check if checkpoint is an ancestor of HEAD
        if not is_ancestor(repo_root, checkpoint, head):
            return False, {
                "error": f"Checkpoint {checkpoint[:8]} is not an ancestor of HEAD {head[:8]}. "
                         f"Run 'synapse index --rebuild' for a full rebuild.",
            }
        
        return _incremental_index(db, repo_root, checkpoint, head)


def _full_index(db: IndexDB, repo_root: str, head: str, is_rebuild: bool = False) -> tuple[bool, dict]:
    """Perform a full index of all tracked files."""
    files = get_tracked_files_at_commit(repo_root, head)
    
    stats = {
        "mode": "rebuild" if is_rebuild else "full",
        "files_scanned": 0,
        "files_processed": 0,
        "files_skipped": 0,
        "files_unsupported": 0,
        "files_error": 0,
        "symbols_found": 0,
        "reparsed": 0,
    }
    
    cursor = db.conn.cursor()
    try:
        if is_rebuild:
            # Clear everything for rebuild
            cursor.execute("DELETE FROM edges")
            cursor.execute("DELETE FROM references_")
            cursor.execute("DELETE FROM calls")
            cursor.execute("DELETE FROM inheritance")
            cursor.execute("DELETE FROM imports")
            cursor.execute("DELETE FROM symbols")
            cursor.execute("DELETE FROM files")
        
        for file_path in files:
            # Normalize path to POSIX
            posix_path = file_path.replace("\\", "/")
            stats["files_scanned"] += 1
            
            if should_exclude_path(posix_path):
                stats["files_skipped"] += 1
                continue
            
            lang = get_language_for_file(posix_path)
            if lang is None:
                stats["files_unsupported"] += 1
                continue
            
            analysis = analyze_file(posix_path, repo_root)
            if analysis is None:
                stats["files_unsupported"] += 1
                continue
            
            if analysis.parse_error:
                stats["files_error"] += 1
            
            db.store_file_analysis(analysis, cursor=cursor)
            stats["files_processed"] += 1
            stats["symbols_found"] += len(analysis.symbols)
            stats["reparsed"] += 1
        
        # Build graph and resolve references across the repository
        build_graph_and_resolve(db, cursor=cursor)
        
        # Set checkpoint in the same transaction
        db.set_checkpoint(head, cursor=cursor)
        db.conn.commit()
        
    except Exception as e:
        db.conn.rollback()
        return False, {"error": f"Indexing failed: {e}"}
    
    stats["checkpoint"] = head
    stats["message"] = f"Indexed {stats['files_processed']} files, {stats['symbols_found']} symbols."
    return True, stats


def _incremental_index(db: IndexDB, repo_root: str, checkpoint: str, head: str) -> tuple[bool, dict]:
    """Perform an incremental index update."""
    changes = get_changed_files(repo_root, checkpoint, head)
    
    stats = {
        "mode": "incremental",
        "files_added": 0,
        "files_modified": 0,
        "files_deleted": 0,
        "files_renamed": 0,
        "files_skipped": 0,
        "symbols_found": 0,
        "reparsed": 0,
    }
    
    cursor = db.conn.cursor()
    try:
        for status, path, new_path in changes:
            posix_path = path.replace("\\", "/")
            
            if status == "D":
                if not should_exclude_path(posix_path):
                    db.delete_file_data(posix_path, cursor=cursor)
                    stats["files_deleted"] += 1
                continue
            
            if status == "R":
                posix_new_path = new_path.replace("\\", "/") if new_path else posix_path
                # Delete old path data
                if not should_exclude_path(posix_path):
                    db.delete_file_data(posix_path, cursor=cursor)
                # Index new path
                if not should_exclude_path(posix_new_path):
                    lang = get_language_for_file(posix_new_path)
                    if lang:
                        analysis = analyze_file(posix_new_path, repo_root)
                        if analysis:
                            db.store_file_analysis(analysis, cursor=cursor)
                            stats["symbols_found"] += len(analysis.symbols)
                            stats["reparsed"] += 1
                    stats["files_renamed"] += 1
                continue
            
            # A or M
            if should_exclude_path(posix_path):
                stats["files_skipped"] += 1
                continue
            
            lang = get_language_for_file(posix_path)
            if lang is None:
                stats["files_skipped"] += 1
                continue
            
            analysis = analyze_file(posix_path, repo_root)
            if analysis is None:
                stats["files_skipped"] += 1
                continue
            
            db.store_file_analysis(analysis, cursor=cursor)
            stats["symbols_found"] += len(analysis.symbols)
            stats["reparsed"] += 1
            
            if status == "A":
                stats["files_added"] += 1
            else:
                stats["files_modified"] += 1
        
        # Re-build graph and re-resolve references across repository
        build_graph_and_resolve(db, cursor=cursor)
        
        db.set_checkpoint(head, cursor=cursor)
        db.conn.commit()
        
    except Exception as e:
        db.conn.rollback()
        return False, {"error": f"Incremental indexing failed: {e}"}
    
    stats["checkpoint"] = head
    total = stats["files_added"] + stats["files_modified"] + stats["files_deleted"] + stats["files_renamed"]
    stats["message"] = f"Incremental update: {total} files changed."
    return True, stats


def _working_tree_index(db: IndexDB, repo_root: str, is_rebuild: bool = False) -> tuple[bool, dict]:
    """Perform an index of the current working tree (including uncommitted and untracked files)."""
    head = get_head_commit(repo_root)
    checkpoint = db.get_checkpoint()

    # If checkpoint is behind HEAD and we're not rebuilding, catch up with HEAD first
    if not is_rebuild and checkpoint and head and checkpoint != head and is_ancestor(repo_root, checkpoint, head):
        ok, inc_stats = _incremental_index(db, repo_root, checkpoint, head)
        if not ok:
            return False, inc_stats

    working_files = get_working_tree_files(repo_root)

    stats = {
        "mode": "working-tree",
        "files_scanned": len(working_files),
        "files_processed": 0,
        "files_deleted": 0,
        "files_skipped": 0,
        "files_unsupported": 0,
        "files_error": 0,
        "symbols_found": 0,
        "reparsed": 0,
    }

    cursor = db.conn.cursor()
    try:
        if is_rebuild or (checkpoint is None and head is None):
            # Clear everything for rebuild
            cursor.execute("DELETE FROM edges")
            cursor.execute("DELETE FROM references_")
            cursor.execute("DELETE FROM calls")
            cursor.execute("DELETE FROM inheritance")
            cursor.execute("DELETE FROM imports")
            cursor.execute("DELETE FROM symbols")
            cursor.execute("DELETE FROM files")

        # 1. Clean up files in index that no longer exist on disk in the working tree
        current_paths = {f.replace("\\", "/") for f in working_files}
        existing_rows = cursor.execute("SELECT path FROM files").fetchall()
        for row in existing_rows:
            p = row["path"]
            if p not in current_paths or not os.path.isfile(os.path.join(repo_root, p.replace("/", os.sep))):
                db.delete_file_data(p, cursor=cursor)
                stats["files_deleted"] += 1

        # 2. Determine which files to parse
        if is_rebuild or (checkpoint is None and head is None):
            files_to_parse = [f for f in working_files if not should_exclude_path(f)]
        else:
            wt_status = get_working_tree_status(repo_root)
            changed_paths = set()
            for st, path, new_path in wt_status:
                if st in ("M", "A"):
                    changed_paths.add(path)
                elif st == "R" and new_path:
                    changed_paths.add(new_path)

            # Also include any valid working tree files missing from DB
            existing_indexed = {r["path"] for r in cursor.execute("SELECT path FROM files").fetchall()}
            for f in working_files:
                if f not in existing_indexed:
                    changed_paths.add(f)

            files_to_parse = [f for f in changed_paths if not should_exclude_path(f)]

        for posix_path in files_to_parse:
            lang = get_language_for_file(posix_path)
            if lang is None:
                stats["files_unsupported"] += 1
                continue

            analysis = analyze_file(posix_path, repo_root)
            if analysis is None:
                stats["files_unsupported"] += 1
                continue

            if analysis.parse_error:
                stats["files_error"] += 1

            db.store_file_analysis(analysis, cursor=cursor)
            stats["files_processed"] += 1
            stats["symbols_found"] += len(analysis.symbols)
            stats["reparsed"] += 1

        # Re-build graph and resolve references across repository
        build_graph_and_resolve(db, cursor=cursor)

        if head:
            db.set_checkpoint(head, cursor=cursor)
        db.set_state("working_tree_indexed", "1", cursor=cursor)
        db.conn.commit()

    except Exception as e:
        db.conn.rollback()
        return False, {"error": f"Working tree indexing failed: {e}"}

    stats["symbols_found"] = db.get_symbol_count()
    stats["checkpoint"] = head or "(uncommitted)"
    stats["message"] = (
        f"Working tree indexed: {stats['files_processed']} file(s) parsed/updated, "
        f"{stats['symbols_found']} total symbols."
    )
    return True, stats


def get_status(repo_root: str) -> dict:
    """Get the current index status."""
    db_path = get_db_path(repo_root)
    
    if not os.path.exists(db_path):
        return {
            "initialized": False,
            "message": "Synapse not initialized. Run 'synapse init' first.",
        }
    
    head = get_head_commit(repo_root)
    dirty = is_working_tree_dirty(repo_root)
    
    with IndexDB(db_path) as db:
        checkpoint = db.get_checkpoint()
        file_count = db.get_file_count()
        symbol_count = db.get_symbol_count()
        edge_count = db.get_edge_count()
        error_count = db.get_error_file_count()
        wt_indexed = db.get_state("working_tree_indexed") == "1"
    
    up_to_date = checkpoint is not None and checkpoint == head
    
    status = {
        "initialized": True,
        "head_commit": head[:8] if head else "(no commits)",
        "checkpoint": checkpoint[:8] if checkpoint else "(not indexed)",
        "up_to_date": up_to_date and not dirty,
        "dirty_working_tree": dirty,
        "files_indexed": file_count,
        "symbols_indexed": symbol_count,
        "edges": edge_count,
        "files_with_errors": error_count,
    }
    
    if wt_indexed:
        status["working_tree_indexed"] = True

    if dirty:
        if wt_indexed:
            status["warning"] = "Working tree has uncommitted changes (currently reflected in working-tree index)."
        else:
            status["warning"] = "Working tree has uncommitted changes not reflected in the index."
    if not up_to_date and checkpoint and head:
        status["warning"] = f"Index is behind HEAD. Run 'synapse index' to update."
    
    return status

