"""Core indexing engine for Synapse."""

from __future__ import annotations

import os
import sys
from typing import Optional

from synapse.git.ops import (
    find_repo_root, get_head_commit, get_all_tracked_files,
    get_changed_files, is_working_tree_dirty, is_ancestor,
    get_tracked_files_at_commit, GitError,
)
from synapse.analysis.dispatcher import analyze_file
from synapse.parsing.parser import get_language_for_file
from synapse.index.store import IndexDB
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
    
    try:
        with IndexDB(db_path) as db:
            version = db.get_state("schema_version")
            return True, f"Synapse initialized successfully (schema v{version})."
    except Exception as e:
        return False, f"Failed to initialize Synapse: {e}"


def run_index(repo_root: str, rebuild: bool = False) -> tuple[bool, dict]:
    """Run the indexing process.
    
    Returns (success, stats_dict).
    """
    db_path = get_db_path(repo_root)
    
    if not os.path.exists(db_path):
        return False, {"error": "Synapse not initialized. Run 'synapse init' first."}
    
    head = get_head_commit(repo_root)
    if head is None:
        return True, {
            "message": "Empty repository (no commits). Nothing to index.",
            "files_processed": 0,
            "symbols_found": 0,
        }
    
    with IndexDB(db_path) as db:
        checkpoint = db.get_checkpoint()
        
        if rebuild or checkpoint is None:
            return _full_index(db, repo_root, head, is_rebuild=rebuild)
        
        if checkpoint == head:
            return True, {
                "message": "Index is up to date. Nothing to do.",
                "files_processed": 0,
                "symbols_found": db.get_symbol_count(),
                "checkpoint": checkpoint,
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
        
        db.set_checkpoint(head, cursor=cursor)
        db.conn.commit()
        
    except Exception as e:
        db.conn.rollback()
        return False, {"error": f"Incremental indexing failed: {e}"}
    
    stats["checkpoint"] = head
    total = stats["files_added"] + stats["files_modified"] + stats["files_deleted"] + stats["files_renamed"]
    stats["message"] = f"Incremental update: {total} files changed."
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
    
    if dirty:
        status["warning"] = "Working tree has uncommitted changes not reflected in the index."
    if not up_to_date and checkpoint and head:
        status["warning"] = f"Index is behind HEAD. Run 'synapse index' to update."
    
    return status
