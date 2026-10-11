"""Git operations for Synapse."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional


class GitError(Exception):
    """Raised when a git operation fails."""
    pass


def _run_git(args: list[str], cwd: str) -> str:
    """Run a git command and return stdout.
    
    Uses list args (never shell=True) with -C <root>.
    """
    cmd = ["git", "-C", cwd] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        raise GitError("Git is not installed or not in PATH")
    except subprocess.TimeoutExpired:
        raise GitError(f"Git command timed out: {' '.join(args)}")
    
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise GitError(f"Git error: {stderr}")
    
    return result.stdout


def find_repo_root(path: str) -> str:
    """Find the git repository root from a given path.
    
    Returns the absolute path to the repo root.
    Raises GitError if not in a git repository.
    """
    try:
        root = _run_git(["rev-parse", "--show-toplevel"], path).strip()
        return os.path.normpath(root)
    except GitError:
        raise GitError(f"Not a git repository: {path}")


def get_head_commit(repo_root: str) -> Optional[str]:
    """Get the current HEAD commit SHA.
    
    Returns None if the repo has no commits.
    """
    try:
        sha = _run_git(["rev-parse", "HEAD"], repo_root).strip()
        return sha
    except GitError:
        return None


def is_ancestor(repo_root: str, ancestor: str, descendant: str) -> bool:
    """Check if ancestor is an ancestor of descendant."""
    try:
        cmd = ["git", "-C", repo_root, "merge-base", "--is-ancestor", ancestor, descendant]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_changed_files(repo_root: str, from_commit: str, to_commit: str) -> list[tuple[str, str, Optional[str]]]:
    """Get files changed between two commits.
    
    Uses git diff --name-status -M -z for rename detection and null-separated parsing.
    
    Returns list of (status, path, new_path_for_renames).
    Status: A (added), M (modified), D (deleted), R (renamed).
    For renames, returns (R, old_path, new_path).
    """
    try:
        output = _run_git(
            ["diff", "--name-status", "-M", "-z", from_commit, to_commit],
            repo_root,
        )
    except GitError as e:
        raise GitError(f"Cannot compute diff: {e}")
    
    if not output:
        return []
    
    # Parse null-separated output
    parts = output.split("\0")
    results = []
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if not part:
            i += 1
            continue
        
        status = part[0]
        
        if status == "R" or status.startswith("R"):
            # Rename: status\0old_path\0new_path
            if i + 2 < len(parts):
                old_path = parts[i + 1]
                new_path = parts[i + 2]
                results.append(("R", old_path, new_path))
                i += 3
            else:
                i += 1
        elif status in ("A", "M", "D"):
            if i + 1 < len(parts):
                filepath = parts[i + 1]
                results.append((status, filepath, None))
                i += 2
            else:
                i += 1
        else:
            # Handle other statuses (T, C, etc.) as modifications
            if i + 1 < len(parts):
                filepath = parts[i + 1]
                results.append(("M", filepath, None))
                i += 2
            else:
                i += 1
    
    return results


def get_all_tracked_files(repo_root: str) -> list[str]:
    """Get all tracked files in the repository.
    
    Uses git ls-files -z for null-separated output.
    """
    try:
        output = _run_git(["ls-files", "-z"], repo_root)
    except GitError:
        return []
    
    if not output:
        return []
    
    files = [f for f in output.split("\0") if f]
    return files


def is_working_tree_dirty(repo_root: str) -> bool:
    """Check if the working tree has uncommitted changes."""
    try:
        output = _run_git(["status", "--porcelain"], repo_root).strip()
        return bool(output)
    except GitError:
        return False


def get_tracked_files_at_commit(repo_root: str, commit: str) -> list[str]:
    """Get all tracked files at a specific commit."""
    try:
        output = _run_git(["ls-tree", "-r", "--name-only", "-z", commit], repo_root)
    except GitError:
        return []
    
    if not output:
        return []
    
    files = [f for f in output.split("\0") if f]
    return files
