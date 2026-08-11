"""
Tests for the example MCP client configs in examples/.

Guards the fix that the stdio config launches the stdio entry point (not the
HTTP server), keeps the examples valid and pointing at real modules, and keeps
the HTTP example's URL aligned with the server defaults.
"""

import importlib.util
import json
from pathlib import Path
from urllib.parse import urlparse

from netops_mcp.config.models import Config

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _load(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text())


class TestStdioExample:
    def test_is_valid_json_with_server_entry(self) -> None:
        cfg = _load("cursor_mcp_config.json")
        assert "netops-mcp" in cfg["mcpServers"]

    def test_launches_stdio_entrypoint_not_http(self) -> None:
        srv = _load("cursor_mcp_config.json")["mcpServers"]["netops-mcp"]
        assert srv["command"] == "python"
        # The fix: stdio must run netops_mcp.server, never the HTTP server.
        assert srv["args"] == ["-m", "netops_mcp.server"]
        assert "netops_mcp.server_http" not in srv["args"]

    def test_referenced_module_is_importable(self) -> None:
        # Ties the example to real code: a module rename would break this.
        assert importlib.util.find_spec("netops_mcp.server") is not None


class TestHttpExample:
    def test_uses_url_form_not_command(self) -> None:
        srv = _load("http_mcp_config.json")["mcpServers"]["netops-mcp"]
        assert "url" in srv
        assert "command" not in srv

    def test_url_matches_server_defaults(self) -> None:
        # Host/port/path defaults live in config.server, not in the
        # NetOpsMCPHTTPServer signature (whose args default to None).
        url = urlparse(_load("http_mcp_config.json")["mcpServers"]["netops-mcp"]["url"])
        server_defaults = Config().server
        assert url.port == server_defaults.port
        assert url.path == server_defaults.path

    def test_referenced_module_is_importable(self) -> None:
        assert importlib.util.find_spec("netops_mcp.server_http") is not None
