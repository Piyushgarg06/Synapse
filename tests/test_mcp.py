"""Tests for Synapse Model Context Protocol (MCP) server."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import pytest

from synapse.core import init_synapse, run_index


def _create_git_repo() -> str:
    """Create a temporary git repository."""
    tmpdir = tempfile.mkdtemp(prefix="synapse_mcp_test_")
    subprocess.run(["git", "init", tmpdir], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.email", "mcp@test.com"], capture_output=True, check=True)
    subprocess.run(["git", "-C", tmpdir, "config", "user.name", "MCPTest"], capture_output=True, check=True)
    return tmpdir


def _commit_all(repo_root: str, message: str) -> str:
    """Add all and commit."""
    subprocess.run(["git", "-C", repo_root, "add", "-A"], capture_output=True, check=True)
    subprocess.run(["git", "-C", repo_root, "commit", "-m", message], capture_output=True, check=True)
    res = subprocess.run(["git", "-C", repo_root, "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    return res.stdout.strip()


class TestSynapseMCPServer:
    """Test MCP tool registration and execution in an isolated process to protect offline audits."""

    def test_mcp_server_registers_all_tools(self):
        script = """
import asyncio
from synapse.mcp import create_mcp_server

server = create_mcp_server()
assert server.instructions and "Synapse" in server.instructions

tools = asyncio.run(server.list_tools())
names = {t.name for t in tools}
expected = {
    "synapse_search",
    "synapse_inspect",
    "synapse_context",
    "synapse_delete_info",
    "synapse_index",
    "synapse_status",
}
assert expected.issubset(names), f"Missing tools: {expected - names}"

prompts = asyncio.run(server.list_prompts())
assert any(p.name == "instructions" for p in prompts)

resources = asyncio.run(server.list_resources())
assert any(str(r.uri) == "synapse://instructions" for r in resources)

print("OK")
"""
        proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True)
        assert "OK" in proc.stdout

    def test_mcp_tool_execution_lifecycle(self):
        repo = _create_git_repo()
        try:
            with open(os.path.join(repo, "math_ops.py"), "w") as f:
                f.write(
                    "def add_numbers(a, b):\n"
                    "    '''Add two numbers.'''\n"
                    "    return a + b\n"
                    "\n"
                    "def calculate_total():\n"
                    "    return add_numbers(10, 20)\n"
                )
            _commit_all(repo, "Initial math ops")
            init_synapse(repo)
            run_index(repo)

            script = f"""
import asyncio
import json
import os
from synapse.mcp import create_mcp_server

repo = {repr(repo)}
server = create_mcp_server()

async def test_all():
    # 1. Search tool
    res_search = await server.call_tool("synapse_search", {{"query": "add_numbers", "repo_path": repo}})
    assert not res_search.is_error
    search_data = json.loads(res_search.content[0].text)
    assert len(search_data) >= 1
    assert search_data[0]["name"] == "add_numbers"

    # 2. Inspect tool
    res_inspect = await server.call_tool("synapse_inspect", {{"symbol": "add_numbers", "repo_path": repo}})
    assert not res_inspect.is_error
    inspect_data = json.loads(res_inspect.content[0].text)
    assert inspect_data["symbol"]["name"] == "add_numbers"
    assert len(inspect_data["callers"]) >= 1

    # 3. Context tool
    res_context = await server.call_tool("synapse_context", {{"symbol": "calculate_total", "repo_path": repo}})
    assert not res_context.is_error
    context_data = json.loads(res_context.content[0].text)
    assert "items" in context_data

    # 4. Delete-info blast radius tool
    res_delete = await server.call_tool("synapse_delete_info", {{"target": "math_ops.py", "symbol": "add_numbers", "repo_path": repo}})
    assert not res_delete.is_error
    del_data = json.loads(res_delete.content[0].text)
    assert del_data["found"] is True
    assert del_data["affected_file_count"] == 1

    # 5. Index working tree tool
    with open(os.path.join(repo, "extra.py"), "w") as f:
        f.write("def uncommitted_work(): pass\\n")

    res_index = await server.call_tool("synapse_index", {{"repo_path": repo, "working_tree": True}})
    assert not res_index.is_error
    index_data = json.loads(res_index.content[0].text)
    assert index_data["success"] is True

    # 6. Status tool
    res_status = await server.call_tool("synapse_status", {{"repo_path": repo}})
    assert not res_status.is_error
    status_data = json.loads(res_status.content[0].text)
    assert status_data["initialized"] is True
    assert status_data.get("working_tree_indexed") is True

asyncio.run(test_all())
print("ALL_TOOLS_PASSED")
"""
            proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True)
            assert "ALL_TOOLS_PASSED" in proc.stdout
        finally:
            shutil.rmtree(repo, ignore_errors=True)
