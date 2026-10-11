"""Synapse CLI — command-line interface."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

from synapse.git.ops import find_repo_root, GitError
from synapse.core import init_synapse, run_index, get_status, get_db_path
from synapse.index.store import IndexDB


def _find_repo() -> str:
    """Find the git repository root from CWD."""
    try:
        return find_repo_root(os.getcwd())
    except GitError:
        print("Error: Not in a git repository.", file=sys.stderr)
        sys.exit(1)


def cmd_init(args: argparse.Namespace) -> int:
    """Handle 'synapse init'."""
    repo_root = _find_repo()
    success, message = init_synapse(repo_root)
    if success:
        print(message)
        return 0
    else:
        print(f"Error: {message}", file=sys.stderr)
        return 1


def cmd_index(args: argparse.Namespace) -> int:
    """Handle 'synapse index'."""
    repo_root = _find_repo()
    rebuild = getattr(args, "rebuild", False)
    success, stats = run_index(repo_root, rebuild=rebuild)
    
    if success:
        if args.json_output:
            print(json.dumps(stats, indent=2))
        else:
            print(stats.get("message", "Indexing complete."))
            if "files_processed" in stats and stats["files_processed"] > 0:
                print(f"  Files processed: {stats['files_processed']}")
                print(f"  Symbols found: {stats['symbols_found']}")
            if "files_added" in stats:
                print(f"  Added: {stats['files_added']}, Modified: {stats['files_modified']}, "
                      f"Deleted: {stats['files_deleted']}, Renamed: {stats['files_renamed']}")
        return 0
    else:
        error = stats.get("error", "Unknown error")
        print(f"Error: {error}", file=sys.stderr)
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    """Handle 'synapse status'."""
    repo_root = _find_repo()
    status = get_status(repo_root)
    
    if args.json_output:
        print(json.dumps(status, indent=2))
    else:
        if not status.get("initialized"):
            print(status.get("message", "Not initialized."))
            return 1
        
        print(f"Synapse Status:")
        print(f"  HEAD commit:    {status['head_commit']}")
        print(f"  Last indexed:   {status['checkpoint']}")
        print(f"  Up to date:     {'yes' if status['up_to_date'] else 'no'}")
        print(f"  Files indexed:  {status['files_indexed']}")
        print(f"  Symbols:        {status['symbols_indexed']}")
        print(f"  Edges:          {status['edges']}")
        if status.get("files_with_errors", 0) > 0:
            print(f"  Parse errors:   {status['files_with_errors']}")
        if status.get("dirty_working_tree"):
            print(f"  [!] Working tree has uncommitted changes not reflected in the index.")
        if status.get("warning"):
            print(f"  [!] {status['warning']}")
    
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """Handle 'synapse search <query>'."""
    repo_root = _find_repo()
    db_path = get_db_path(repo_root)
    
    if not os.path.exists(db_path):
        print("Error: Synapse not initialized. Run 'synapse init' first.", file=sys.stderr)
        return 1
    
    query = args.query
    limit = args.limit
    
    with IndexDB(db_path) as db:
        results = db.search_symbols(query, limit=limit)
    
    if args.json_output:
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print(f"No results found for '{query}'.")
            return 0
        
        print(f"Found {len(results)} result(s) for '{query}':")
        for r in results:
            print(f"  {r['kind']:8s}  {r['qualified_name']}  ({r['file_path']}:{r['start_line']})")
    
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Handle 'synapse inspect <symbol>'."""
    repo_root = _find_repo()
    db_path = get_db_path(repo_root)
    
    if not os.path.exists(db_path):
        print("Error: Synapse not initialized. Run 'synapse init' first.", file=sys.stderr)
        return 1
    
    # Stub for Phase 5
    print("Inspect command will be implemented in Phase 5.", file=sys.stderr)
    return 0


def cmd_context(args: argparse.Namespace) -> int:
    """Handle 'synapse context <query>'."""
    repo_root = _find_repo()
    db_path = get_db_path(repo_root)
    
    if not os.path.exists(db_path):
        print("Error: Synapse not initialized. Run 'synapse init' first.", file=sys.stderr)
        return 1
    
    # Stub for Phase 5
    print("Context command will be implemented in Phase 5.", file=sys.stderr)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Handle 'synapse export <format>'."""
    repo_root = _find_repo()
    db_path = get_db_path(repo_root)
    
    if not os.path.exists(db_path):
        print("Error: Synapse not initialized. Run 'synapse init' first.", file=sys.stderr)
        return 1
    
    # Stub for Phase 6
    print(f"Export {args.format} will be implemented in Phase 6.", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="synapse",
        description="Synapse: Repository Intelligence Engine — local-first structural analysis and retrieval",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # init
    init_parser = subparsers.add_parser("init", help="Initialize Synapse in a Git repository")
    init_parser.set_defaults(func=cmd_init)
    
    # index
    index_parser = subparsers.add_parser("index", help="Index the repository (initial or incremental)")
    index_parser.add_argument("--rebuild", action="store_true", help="Force a full rebuild of the index")
    index_parser.add_argument("--json", dest="json_output", action="store_true", help="Output as JSON")
    index_parser.set_defaults(func=cmd_index)
    
    # status
    status_parser = subparsers.add_parser("status", help="Show index status and statistics")
    status_parser.add_argument("--json", dest="json_output", action="store_true", help="Output as JSON")
    status_parser.set_defaults(func=cmd_status)
    
    # search
    search_parser = subparsers.add_parser("search", help="Search for symbols and files")
    search_parser.add_argument("query", help="Search query (symbol or file name)")
    search_parser.add_argument("--limit", type=int, default=20, help="Maximum results (default: 20)")
    search_parser.add_argument("--json", dest="json_output", action="store_true", help="Output as JSON")
    search_parser.set_defaults(func=cmd_search)
    
    # inspect
    inspect_parser = subparsers.add_parser("inspect", help="Inspect a symbol's definition and relationships")
    inspect_parser.add_argument("symbol", help="Symbol name to inspect")
    inspect_parser.add_argument("--depth", type=int, default=1, help="Traversal depth (default: 1)")
    inspect_parser.add_argument("--json", dest="json_output", action="store_true", help="Output as JSON")
    inspect_parser.set_defaults(func=cmd_inspect)
    
    # context
    context_parser = subparsers.add_parser("context", help="Retrieve focused repository context")
    context_parser.add_argument("query", help="Context query")
    context_parser.add_argument("--max-results", type=int, default=10, help="Max results (default: 10)")
    context_parser.add_argument("--max-bytes", type=int, default=8192, help="Max bytes per snippet (default: 8192)")
    context_parser.add_argument("--depth", type=int, default=2, help="Traversal depth (default: 2)")
    context_parser.add_argument("--output", type=str, help="Output file path")
    context_parser.add_argument("--json", dest="json_output", action="store_true", help="Output as JSON")
    context_parser.set_defaults(func=cmd_context)
    
    # export
    export_parser = subparsers.add_parser("export", help="Export index data")
    export_parser.add_argument("format", choices=["json", "md", "zip"], help="Export format")
    export_parser.add_argument("--output", type=str, help="Output file path")
    export_parser.set_defaults(func=cmd_export)
    
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    
    if not args.command:
        parser.print_help()
        return 2
    
    # Ensure json_output exists for commands that don't have it
    if not hasattr(args, "json_output"):
        args.json_output = False
    
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
