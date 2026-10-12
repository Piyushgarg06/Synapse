"""Auto-installer and configurator for Synapse MCP across AI clients.

Supports automatic detection and configuration for:
- Antigravity / Gemini IDE
- Claude Desktop
- Claude Code (CLI)
- Cursor (global and project-level)
- Windsurf (Codeium)
- VS Code Extensions (Cline, Roo Code)
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Any, Optional


def _get_platform() -> str:
    system = platform.system().lower()
    if "darwin" in system:
        return "darwin"
    elif "windows" in system:
        return "windows"
    return "linux"


def _get_claude_desktop_path() -> Path:
    plat = _get_platform()
    if plat == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif plat == "windows":
        appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    else:
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def _get_claude_code_path() -> Path:
    return Path.home() / ".claude.json"


def _get_antigravity_path(project_root: Optional[str] = None) -> Path:
    if project_root:
        return Path(project_root) / ".agents" / "mcp_config.json"
    return Path.home() / ".gemini" / "config" / "mcp_config.json"


def _get_cursor_path(project_root: Optional[str] = None) -> Path:
    if project_root:
        return Path(project_root) / ".cursor" / "mcp.json"
    return Path.home() / ".cursor" / "mcp.json"


def _get_windsurf_path() -> Path:
    return Path.home() / ".codeium" / "windsurf" / "mcp_config.json"


def _get_cline_path() -> Path:
    plat = _get_platform()
    if plat == "darwin":
        base = Path.home() / "Library" / "Application Support" / "Code" / "User" / "globalStorage"
    elif plat == "windows":
        appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        base = Path(appdata) / "Code" / "User" / "globalStorage"
    else:
        base = Path.home() / ".config" / "Code" / "User" / "globalStorage"
    return base / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"


def _get_roo_path() -> Path:
    plat = _get_platform()
    if plat == "darwin":
        base = Path.home() / "Library" / "Application Support" / "Code" / "User" / "globalStorage"
    elif plat == "windows":
        appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        base = Path(appdata) / "Code" / "User" / "globalStorage"
    else:
        base = Path.home() / ".config" / "Code" / "User" / "globalStorage"
    return base / "rooveterinaryinc.roo-cline" / "settings" / "cline_mcp_settings.json"


class ClientTarget:
    """Represents a supported AI IDE / agent client target."""

    def __init__(
        self,
        name: str,
        display_name: str,
        config_path: Path,
        app_dir: Optional[Path] = None,
        is_extension: bool = False,
    ):
        self.name = name
        self.display_name = display_name
        self.config_path = config_path
        self.app_dir = app_dir or config_path.parent
        self.is_extension = is_extension

    def is_detected(self) -> bool:
        """Return True if the client or its config directory exists."""
        return self.config_path.exists() or self.app_dir.exists()

    def is_configured(self) -> bool:
        """Return True if Synapse is currently configured in this target."""
        if not self.config_path.exists():
            return False
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            servers = data.get("mcpServers", {})
            return "synapse" in servers
        except Exception:
            return False


def get_all_targets(project_root: Optional[str] = None) -> list[ClientTarget]:
    """Get all supported client targets for current environment."""
    targets = [
        ClientTarget(
            name="antigravity",
            display_name="Antigravity / Gemini",
            config_path=_get_antigravity_path(project_root),
            app_dir=Path(project_root) / ".agents" if project_root else Path.home() / ".gemini",
        ),
        ClientTarget(
            name="cursor",
            display_name="Cursor",
            config_path=_get_cursor_path(project_root),
            app_dir=Path(project_root) / ".cursor" if project_root else Path.home() / ".cursor",
        ),
        ClientTarget(
            name="claude-desktop",
            display_name="Claude Desktop",
            config_path=_get_claude_desktop_path(),
            app_dir=_get_claude_desktop_path().parent,
        ),
        ClientTarget(
            name="claude-code",
            display_name="Claude Code",
            config_path=_get_claude_code_path(),
            app_dir=Path.home() / ".claude",
        ),
        ClientTarget(
            name="windsurf",
            display_name="Windsurf",
            config_path=_get_windsurf_path(),
            app_dir=_get_windsurf_path().parent,
        ),
        ClientTarget(
            name="cline",
            display_name="Cline (VS Code)",
            config_path=_get_cline_path(),
            app_dir=_get_cline_path().parent,
            is_extension=True,
        ),
        ClientTarget(
            name="roo",
            display_name="Roo Code (VS Code)",
            config_path=_get_roo_path(),
            app_dir=_get_roo_path().parent,
            is_extension=True,
        ),
    ]
    return targets


def _get_server_entry(target_name: str) -> dict[str, Any]:
    """Generate the MCP configuration dictionary for Synapse."""
    entry: dict[str, Any] = {
        "command": "synapse",
        "args": ["mcp"],
    }
    if target_name in ("cline", "roo"):
        entry["disabled"] = False
        entry["autoApprove"] = []
    return entry


def _read_config(path: Path) -> dict[str, Any]:
    """Read existing JSON config, or return empty dict."""
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Create a backup before modifying corrupt/non-standard file
        bak_path = path.with_suffix(path.suffix + ".bak")
        try:
            shutil.copyfile(path, bak_path)
            print(f"  [!] Backed up invalid JSON to {bak_path}")
        except OSError:
            pass
        return {}
    except OSError:
        return {}


def _write_config(path: Path, data: dict[str, Any]) -> bool:
    """Safely write JSON configuration to target path."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        return True
    except OSError as e:
        print(f"  [!] Failed to write {path}: {e}", file=sys.stderr)
        return False


def install_mcp(target: str = "all", project: bool = False) -> int:
    """Install Synapse MCP configuration into detected or specified targets."""
    project_root = None
    if project:
        from synapse.git.ops import find_repo_root, GitError
        try:
            project_root = find_repo_root(os.getcwd())
        except GitError:
            project_root = os.getcwd()

    targets = get_all_targets(project_root)
    normalized_target = target.lower().strip()

    # Filter targets
    if normalized_target != "all":
        selected = [t for t in targets if t.name == normalized_target or normalized_target in t.name]
        if not selected:
            valid_names = ", ".join(t.name for t in targets)
            print(f"Error: Unknown target '{target}'. Valid targets: all, {valid_names}", file=sys.stderr)
            return 1
    else:
        # For 'all', prioritize detected targets
        detected = [t for t in targets if t.is_detected()]
        if not detected:
            print("No supported AI IDE configurations detected automatically.")
            print("Configuring standard clients (Claude Desktop, Antigravity, Cursor)...")
            selected = [t for t in targets if t.name in ("antigravity", "cursor", "claude-desktop")]
        else:
            selected = detected

    print(f"Configuring Synapse MCP for {len(selected)} client(s)...")
    success_count = 0

    for t in selected:
        config = _read_config(t.config_path)
        if "mcpServers" not in config or not isinstance(config["mcpServers"], dict):
            config["mcpServers"] = {}

        config["mcpServers"]["synapse"] = _get_server_entry(t.name)

        if _write_config(t.config_path, config):
            print(f"  [+] {t.display_name:22} -> {t.config_path}")
            success_count += 1

    print(f"\nSuccessfully configured {success_count}/{len(selected)} client(s).")
    print("Restart your IDE or agent session for changes to take effect.")
    return 0 if success_count > 0 else 1


def uninstall_mcp(target: str = "all", project: bool = False) -> int:
    """Remove Synapse MCP configuration from targets."""
    project_root = None
    if project:
        from synapse.git.ops import find_repo_root, GitError
        try:
            project_root = find_repo_root(os.getcwd())
        except GitError:
            project_root = os.getcwd()

    targets = get_all_targets(project_root)
    normalized_target = target.lower().strip()

    if normalized_target != "all":
        selected = [t for t in targets if t.name == normalized_target or normalized_target in t.name]
    else:
        selected = [t for t in targets if t.config_path.exists()]

    if not selected:
        print("No configured clients found.")
        return 0

    removed_count = 0
    for t in selected:
        if not t.config_path.exists():
            continue

        config = _read_config(t.config_path)
        if "mcpServers" in config and "synapse" in config["mcpServers"]:
            del config["mcpServers"]["synapse"]
            if _write_config(t.config_path, config):
                print(f"  [-] Removed from {t.display_name}: {t.config_path}")
                removed_count += 1

    print(f"\nSynapse MCP uninstalled from {removed_count} client(s).")
    return 0


def status_mcp(project: bool = False) -> int:
    """Display current MCP installation status across all supported clients."""
    project_root = None
    if project:
        from synapse.git.ops import find_repo_root, GitError
        try:
            project_root = find_repo_root(os.getcwd())
        except GitError:
            project_root = os.getcwd()

    targets = get_all_targets(project_root)
    print("Synapse MCP Client Status:")
    for t in targets:
        detected = t.is_detected()
        configured = t.is_configured()

        if configured:
            status = "[+] Configured"
        elif detected:
            status = "[*] Detected (not configured)"
        else:
            status = "[-] Not detected"

        print(f"  {status:30} {t.display_name:22} ({t.config_path})")

    print("\nTip: Run 'synapse mcp install' to auto-configure detected clients.")
    return 0
