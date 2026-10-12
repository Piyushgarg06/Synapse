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
    working_tree = getattr(args, "working_tree", False)
    success, stats = run_index(repo_root, rebuild=rebuild, working_tree=working_tree)
    
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
        if status.get("working_tree_indexed"):
            print("  Working tree:   indexed (uncommitted changes reflected in index)")
        elif status.get("dirty_working_tree"):
            print("  [!] Working tree has uncommitted changes not reflected in the index.")
        if status.get("warning") and not status.get("working_tree_indexed"):
            print(f"  [!] {status['warning']}")
    
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """Handle 'synapse search <query>'."""
    repo_root = _find_repo()
    db_path = get_db_path(repo_root)
    
    if not os.path.exists(db_path):
        print("Error: Synapse not initialized. Run 'synapse init' first.", file=sys.stderr)
        return 1
    
    from synapse.retrieval.engine import search_symbols_and_files
    query = args.query
    limit = args.limit
    
    with IndexDB(db_path) as db:
        results = search_symbols_and_files(db, query, limit=limit)
    
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
    
    from synapse.retrieval.engine import inspect_symbol
    with IndexDB(db_path) as db:
        result = inspect_symbol(db, args.symbol, depth=getattr(args, "depth", 1))
    
    if args.json_output:
        print(json.dumps(result, indent=2))
        return 0
    
    if not result.get("found"):
        print(result.get("message", "Symbol not found."))
        return 0
    
    if result.get("ambiguous"):
        print(result.get("message"))
        for c in result.get("candidates", []):
            print(f"  - {c['kind']:8s} {c['qualified_name']} ({c['file_path']}:{c['line']}) [id: {c['id']}]")
        return 0
    
    sym = result["symbol"]
    print(f"Symbol: {sym['qualified_name']} ({sym['kind']})")
    print(f"  File:     {sym['file_path']}:{sym['start_line']}-{sym['end_line']}")
    print(f"  ID:       {sym['id']}")
    
    if result.get("parent"):
        print(f"  Defined in: {result['parent']['qualified_name']} ({result['parent']['kind']})")
    
    if result.get("base_classes"):
        print("  Inherits from:")
        for b in result["base_classes"]:
            print(f"    - {b['qualified_name']} ({b['file_path']}:{b['start_line']})")
            
    if result.get("subclasses"):
        print("  Subclasses:")
        for s in result["subclasses"]:
            print(f"    - {s['qualified_name']} ({s['file_path']}:{s['start_line']})")
            
    if result.get("callers"):
        print("  Callers:")
        for c in result["callers"]:
            print(f"    - {c['qualified_name']} ({c['file_path']}:{c['start_line']})")
            
    if result.get("callees"):
        print("  Calls:")
        for c in result["callees"]:
            print(f"    - {c['qualified_name']} ({c['file_path']}:{c['start_line']})")
            
    if result.get("unresolved_references"):
        print("  Unresolved references:")
        for u in result["unresolved_references"]:
            print(f"    - [UNRESOLVED] {u['name']} (line {u['start_line']})")
            
    return 0


def cmd_context(args: argparse.Namespace) -> int:
    """Handle 'synapse context <query>'."""
    repo_root = _find_repo()
    db_path = get_db_path(repo_root)
    
    if not os.path.exists(db_path):
        print("Error: Synapse not initialized. Run 'synapse init' first.", file=sys.stderr)
        return 1
    
    from synapse.retrieval.engine import generate_context
    with IndexDB(db_path) as db:
        ctx = generate_context(
            db,
            repo_root,
            args.query,
            max_results=getattr(args, "max_results", 10),
            max_bytes=getattr(args, "max_bytes", 8192),
            depth=getattr(args, "depth", 2),
        )
    
    output_content = ""
    if args.json_output:
        output_content = json.dumps(ctx, indent=2)
    else:
        out_lines = [
            f"# Synapse Repository Context: {ctx['query']}",
            f"",
            f"{ctx['disclaimer']}",
            f"",
            f"Found {ctx['results_count']} item(s):",
            f"",
        ]
        for it in ctx.get("items", []):
            out_lines.append(f"## {it['kind'].capitalize()}: {it['qualified_name']}")
            out_lines.append(f"Path: `{it['file_path']}` (Lines {it['start_line']}-{it['end_line']})")
            out_lines.append(f"Reason: {it['reason']}")
            if it.get("is_stale"):
                out_lines.append("Warning: [!] File changed on disk since last indexing; snippet may not reflect working tree.")
            out_lines.append("```")
            out_lines.append(it['snippet'].rstrip())
            out_lines.append("```")
            if it.get("callees"):
                out_lines.append("Calls:")
                for c in it["callees"]:
                    out_lines.append(f"  - {c['qualified_name']} ({c['file_path']}:{c['start_line']})")
            out_lines.append("")
            
        if ctx.get("unresolved_dependencies"):
            out_lines.append("## Unresolved References:")
            for u in ctx["unresolved_dependencies"]:
                out_lines.append(f"- `{u['reference']}` in `{u['symbol']}` ({u['file_path']}:{u['line']})")
            out_lines.append("")
            
        output_content = "\n".join(out_lines)
    
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_content)
            print(f"Context written to {args.output}")
        except Exception as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            return 1
    else:
        print(output_content)
        
    return 0


def cmd_delete_info(args: argparse.Namespace) -> int:
    """Handle 'synapse delete-info <target> [symbol]'."""
    repo_root = _find_repo()
    db_path = get_db_path(repo_root)

    if not os.path.exists(db_path):
        print("Error: Synapse not initialized. Run 'synapse init' first.", file=sys.stderr)
        return 1

    from synapse.analysis.impact import analyze_file_deletion, analyze_symbol_deletion

    target = args.target
    symbol = getattr(args, "symbol", None)

    with IndexDB(db_path) as db:
        if symbol:
            # Analyse deletion of a specific symbol scoped to file_path
            result = analyze_symbol_deletion(db, symbol, file_path=target)
        else:
            # Try as file path first, then as symbol name
            result = analyze_file_deletion(db, target)
            if not result.get("found"):
                result = analyze_symbol_deletion(db, target)

    if args.json_output:
        print(json.dumps(result, indent=2))
        return 0

    if not result.get("found"):
        query = f"{target} {symbol}" if symbol else target
        print(f"'{query}' not found in the index.")
        return 0

    if result.get("ambiguous"):
        print("Ambiguous query. Multiple matches found:")
        for c in result["candidates"]:
            if "kind" in c:
                print(f"  - {c['kind']:8s} {c['qualified_name']} ({c['file_path']}:{c['start_line']})")
            else:
                print(f"  - {c.get('path', c)}")
        print("Specify the fully qualified name or more specific path.")
        return 0

    # --- File deletion report ---
    if "symbols_lost" in result:
        print(f"\n{'='*60}")
        print(f"  DELETION IMPACT: {result['file_path']}")
        print(f"{'='*60}")
        print(f"  Language:       {result['language']}")
        print(f"  Symbols lost:   {len(result['symbols_lost'])}")
        print(f"  Affected files: {result['affected_file_count']}")
        print(f"  Broken links:   {result['total_broken_links']}")

        if result["symbols_lost"]:
            print(f"\n  Symbols that would be removed:")
            for s in result["symbols_lost"]:
                print(f"    - {s['kind']:8s} {s['qualified_name']} (line {s['start_line']})")

        deps = result["dependents"]

        if deps["importers"]:
            print(f"\n  Files that import from this module ({len(deps['importers'])}):")
            for imp in deps["importers"]:
                names = f" ({imp['imported_names']})" if imp.get("imported_names") else ""
                print(f"    [-] {imp['file_path']}:{imp.get('start_line', 1)}{names}")

        if deps["callers"]:
            print(f"\n  External callers that would break ({len(deps['callers'])}):")
            for c in deps["callers"]:
                print(f"    [-] {c['qualified_name']} ({c['file_path']}:{c['start_line']}) calls {c['calls_symbol']}")

        if deps["subclasses"]:
            print(f"\n  Subclasses that would lose their base ({len(deps['subclasses'])}):")
            for s in deps["subclasses"]:
                print(f"    [-] {s['qualified_name']} ({s['file_path']}:{s['start_line']}) inherits {s['inherits_from']}")

        if deps["references"]:
            print(f"\n  Resolved references that would break ({len(deps['references'])}):")
            for r in deps["references"]:
                ctx = f" in {r['context_qualified_name']}" if r.get("context_qualified_name") else ""
                print(f"    [-] {r['file_path']}:{r['start_line']} -> {r['name']}{ctx}")

        if result["affected_file_count"] == 0:
            print(f"\n  [+] Safe to delete - no other files depend on this.")
        else:
            print(f"\n  [!] {result['affected_file_count']} file(s) would be affected:")
            for fp in result["affected_files"]:
                print(f"    - {fp}")

        print()
        return 0

    # --- Symbol deletion report ---
    sym = result["symbol"]
    print(f"\n{'='*60}")
    print(f"  DELETION IMPACT: {sym['qualified_name']} ({sym['kind']})")
    print(f"{'='*60}")
    print(f"  File:           {sym['file_path']}:{sym['start_line']}-{sym['end_line']}")
    print(f"  Affected files: {result['affected_file_count']}")
    print(f"  Broken links:   {result['total_broken_links']}")

    if result.get("children_lost"):
        print(f"\n  Child symbols that would also be removed ({len(result['children_lost'])}):")
        for ch in result["children_lost"]:
            print(f"    - {ch['kind']:8s} {ch['qualified_name']} (line {ch['start_line']})")

    deps = result["dependents"]

    if deps["callers"]:
        print(f"\n  Callers that would break ({len(deps['callers'])}):")
        for c in deps["callers"]:
            print(f"    [-] {c['qualified_name']} ({c['file_path']}:{c['start_line']})")

    if deps["subclasses"]:
        print(f"\n  Subclasses that would lose their base ({len(deps['subclasses'])}):")
        for s in deps["subclasses"]:
            print(f"    [-] {s['qualified_name']} ({s['file_path']}:{s['start_line']})")

    if deps["references"]:
        print(f"\n  Resolved references that would break ({len(deps['references'])}):")
        for r in deps["references"]:
            ctx = f" in {r['context_qualified_name']}" if r.get("context_qualified_name") else ""
            print(f"    [-] {r['file_path']}:{r['start_line']} -> {r['name']}{ctx}")

    if result["affected_file_count"] == 0:
        print(f"\n  [+] Safe to delete - no other code depends on this symbol.")
    else:
        print(f"\n  [!] {result['affected_file_count']} file(s) would be affected:")
        for fp in result["affected_files"]:
            print(f"    - {fp}")

    print()
    return 0



def cmd_export(args: argparse.Namespace) -> int:
    """Handle 'synapse export <format>'."""
    repo_root = _find_repo()
    db_path = get_db_path(repo_root)
    
    if not os.path.exists(db_path):
        print("Error: Synapse not initialized. Run 'synapse init' first.", file=sys.stderr)
        return 1
    
    from synapse.export.exporter import export_json, export_markdown, export_zip
    
    with IndexDB(db_path) as db:
        fmt = args.format.lower()
        if fmt == "json":
            data = export_json(db, repo_root)
            json_text = json.dumps(data, indent=2, sort_keys=True)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(json_text)
                print(f"Exported JSON index to {args.output}")
            else:
                print(json_text)
                
        elif fmt == "md":
            md_text = export_markdown(db)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(md_text)
                print(f"Exported Markdown overview to {args.output}")
            else:
                print(md_text)
                
        elif fmt == "zip":
            out_path = args.output or os.path.join(repo_root, "synapse_export.zip")
            export_zip(db, out_path, repo_root)
            print(f"Exported ZIP snapshot to {out_path}")
            
        else:
            print(f"Error: Unknown export format '{args.format}'", file=sys.stderr)
            return 2
            
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
    index_parser.add_argument("--working-tree", action="store_true", help="Index the uncommitted working tree (staged, modified, and untracked files)")
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
    context_parser.add_argument("-o", "--output", type=str, help="Output file path")
    context_parser.add_argument("--json", dest="json_output", action="store_true", help="Output as JSON")
    context_parser.set_defaults(func=cmd_context)
    
    # delete-info
    delete_info_parser = subparsers.add_parser(
        "delete-info",
        help="Show blast-radius impact of deleting a file or symbol",
    )
    delete_info_parser.add_argument("target", help="File path or symbol name to analyse")
    delete_info_parser.add_argument("symbol", nargs="?", default=None, help="Specific symbol within the file (optional)")
    delete_info_parser.add_argument("--json", dest="json_output", action="store_true", help="Output as JSON")
    delete_info_parser.set_defaults(func=cmd_delete_info)

    # export
    export_parser = subparsers.add_parser("export", help="Export index data")
    export_parser.add_argument("format", choices=["json", "md", "zip"], help="Export format")
    export_parser.add_argument("-o", "--output", type=str, help="Output file path")
    export_parser.set_defaults(func=cmd_export)

    # mcp
    mcp_parser = subparsers.add_parser(
        "mcp",
        help="Start the Model Context Protocol (MCP) server for Claude Code, Gemini, and Codex",
    )
    mcp_parser.set_defaults(func=cmd_mcp)

    return parser


def cmd_mcp(args: argparse.Namespace) -> int:
    """Handle 'synapse mcp'."""
    from synapse.mcp import main as run_mcp
    run_mcp()
    return 0



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
