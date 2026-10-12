"""Model Context Protocol (MCP) Server for Synapse.

Exposes Synapse's repository knowledge graph, semantic retrieval,
bounded context generation, and deletion impact analysis to AI coding agents
including Claude Code, Gemini CLI, Cursor, Windsurf, and Codex.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Optional

from synapse.core import init_synapse, run_index, get_status, get_db_path
from synapse.git.ops import find_repo_root, GitError
from synapse.index.store import IndexDB
from synapse.retrieval.engine import (
    search_symbols_and_files,
    inspect_symbol,
    generate_context,
)
from synapse.analysis.impact import analyze_file_deletion, analyze_symbol_deletion


def _resolve_repo(repo_path: str = "") -> tuple[str, str]:
    """Resolve repository root and ensure database is initialized."""
    target_dir = os.path.abspath(repo_path.strip()) if repo_path and repo_path.strip() else os.getcwd()
    try:
        root = find_repo_root(target_dir)
    except GitError:
        root = target_dir

    db_path = get_db_path(root)
    if not os.path.exists(db_path):
        init_synapse(root)

    return root, db_path


def _load_instructions() -> str:
    """Load instructions markdown bundled with Synapse."""
    path = os.path.join(os.path.dirname(__file__), "mcp_instructions.md")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            pass
    return "Synapse repository intelligence and code knowledge graph MCP server."


def create_mcp_server():
    """Create and configure the Synapse MCP Server."""
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError:
        try:
            from mcp.server.fastmcp import FastMCP as MCPServer
        except ImportError:
            raise RuntimeError(
                "MCP library is required to run the server. Install it via 'pip install mcp'."
            )

    instructions = _load_instructions()
    try:
        server = MCPServer("synapse", instructions=instructions)
    except TypeError:
        server = MCPServer("synapse")

    @server.prompt(name="instructions")
    def synapse_instructions() -> str:
        """Return instructions and recommended workflow for Synapse MCP tools."""
        return _load_instructions()

    @server.resource("synapse://instructions")
    def get_instructions_resource() -> str:
        """Instructions and guide for using Synapse MCP tools."""
        return _load_instructions()

    @server.tool(
        description=(
            "Search symbols (functions, classes, methods) and file paths in .synapse/index.db. "
            "Use this instead of manually crawling directories to discover where code is defined."
        )
    )
    def synapse_search(query: str, repo_path: str = "", limit: int = 20) -> str:
        """Search symbols and files in the repository."""
        root, db_path = _resolve_repo(repo_path)
        with IndexDB(db_path) as db:
            results = search_symbols_and_files(db, query, limit=limit)
        return json.dumps(results, indent=2)

    @server.tool(
        description=(
            "Inspect a specific code symbol from .synapse/index.db. Returns definition location, "
            "docstring, incoming callers, outgoing callees, inheritance hierarchy, and references. "
            "Always inspect a symbol here before modifying it."
        )
    )
    def synapse_inspect(symbol: str, repo_path: str = "", depth: int = 1) -> str:
        """Inspect a symbol's definition, callers, callees, and inheritance."""
        root, db_path = _resolve_repo(repo_path)
        with IndexDB(db_path) as db:
            data = inspect_symbol(db, symbol, depth=depth)
        return json.dumps(data, indent=2)

    @server.tool(
        description=(
            "Generate bounded, high-signal context snippet bundles directly from the .synapse/index.db "
            "knowledge graph. Includes target definition, callers, dependencies, and type context "
            "strictly bounded within a token budget. Use this instead of dumping entire files."
        )
    )
    def synapse_context(symbol: str, repo_path: str = "", depth: int = 2, budget: int = 8000) -> str:
        """Generate high-density context for code generation or editing."""
        root, db_path = _resolve_repo(repo_path)
        with IndexDB(db_path) as db:
            data = generate_context(db, root, symbol, max_bytes=budget, depth=depth)
        return json.dumps(data, indent=2)

    @server.tool(
        description=(
            "Query .synapse/index.db for blast-radius impact analysis before modifying or deleting code. "
            "Shows every external file that would break, callers, subclasses, importers, and references."
        )
    )
    def synapse_delete_info(target: str, symbol: str = "", repo_path: str = "") -> str:
        """Show blast radius of deleting or altering a file or symbol."""
        root, db_path = _resolve_repo(repo_path)
        with IndexDB(db_path) as db:
            if symbol.strip():
                result = analyze_symbol_deletion(db, symbol.strip(), file_path=target.strip())
            else:
                result = analyze_file_deletion(db, target.strip())
                if not result.get("found"):
                    result = analyze_symbol_deletion(db, target.strip())
        return json.dumps(result, indent=2)

    @server.tool(
        description=(
            "Index the repository into .synapse/index.db. If working_tree is true (default), uncommitted "
            "changes and untracked files are immediately indexed so all AI models share updated context."
        )
    )
    def synapse_index(repo_path: str = "", working_tree: bool = True, rebuild: bool = False) -> str:
        """Index or update repository knowledge graph."""
        root, db_path = _resolve_repo(repo_path)
        success, stats = run_index(root, rebuild=rebuild, working_tree=working_tree)
        return json.dumps({"success": success, **stats}, indent=2)

    @server.tool(
        description=(
            "Get the current index status of .synapse/index.db: indexed file and symbol counts, "
            "graph edge counts, HEAD commit, checkpoint, and working tree dirty/indexed flags."
        )
    )
    def synapse_status(repo_path: str = "") -> str:
        """Get Synapse index status."""
        root, db_path = _resolve_repo(repo_path)
        status = get_status(root)
        return json.dumps(status, indent=2)

    return server


def main():
    """Run the Synapse MCP server on stdio."""
    server = create_mcp_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
