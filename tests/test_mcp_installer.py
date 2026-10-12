"""Tests for Synapse MCP auto-installer and configuration management."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from synapse.mcp_installer import (
    ClientTarget,
    get_all_targets,
    install_mcp,
    uninstall_mcp,
    status_mcp,
    _read_config,
    _write_config,
)


class TestMCPInstaller(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_read_and_write_config(self):
        cfg_path = self.workspace / "sub" / "mcp.json"
        data = {"mcpServers": {"test": {"command": "echo"}}}
        self.assertTrue(_write_config(cfg_path, data))
        self.assertTrue(cfg_path.exists())

        read_data = _read_config(cfg_path)
        self.assertEqual(read_data, data)

    def test_read_corrupt_config_creates_backup(self):
        cfg_path = self.workspace / "corrupt.json"
        cfg_path.write_text("{invalid json", encoding="utf-8")
        read_data = _read_config(cfg_path)
        self.assertEqual(read_data, {})
        self.assertTrue((self.workspace / "corrupt.json.bak").exists())

    def test_install_and_uninstall_project(self):
        # Test project-level install
        code = install_mcp(target="cursor", project=True)
        # Check project target path
        cursor_cfg = Path.cwd() / ".cursor" / "mcp.json"
        try:
            self.assertEqual(code, 0)
            self.assertTrue(cursor_cfg.exists())

            with open(cursor_cfg, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertIn("synapse", data["mcpServers"])
            self.assertEqual(data["mcpServers"]["synapse"]["command"], "synapse")
            self.assertEqual(data["mcpServers"]["synapse"]["args"], ["mcp"])

            # Test uninstall
            un_code = uninstall_mcp(target="cursor", project=True)
            self.assertEqual(un_code, 0)
            with open(cursor_cfg, "r", encoding="utf-8") as f:
                un_data = json.load(f)
            self.assertNotIn("synapse", un_data.get("mcpServers", {}))
        finally:
            if cursor_cfg.exists():
                cursor_cfg.unlink()
            if cursor_cfg.parent.exists():
                try:
                    cursor_cfg.parent.rmdir()
                except OSError:
                    pass

    def test_status_mcp(self):
        ret = status_mcp(project=False)
        self.assertEqual(ret, 0)

    def test_custom_mock_target_install(self):
        fake_cfg = self.workspace / "mock_client" / "config.json"
        target = ClientTarget("mock", "Mock Client", fake_cfg)

        with patch("synapse.mcp_installer.get_all_targets", return_value=[target]):
            # install
            res = install_mcp(target="mock")
            self.assertEqual(res, 0)
            self.assertTrue(fake_cfg.exists())
            self.assertTrue(target.is_configured())

            # uninstall
            un_res = uninstall_mcp(target="mock")
            self.assertEqual(un_res, 0)
            self.assertFalse(target.is_configured())


if __name__ == "__main__":
    unittest.main()
