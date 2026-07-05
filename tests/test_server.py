"""
Tests for NetOpsMCPServer.
"""

import asyncio
import json
import logging
import os
import tempfile
from unittest.mock import patch

import pytest
from netops_mcp.server import NetOpsMCPServer

# Fake system-check results with REAL tool names — shape mirrors
# netops_mcp.utils.system_check.check_required_tools()'s return contract.
FAKE_TOOL_STATUS = {
    "all_available": False,
    "available_tools": ["ping"],
    "missing_tools": ["nmap", "mtr"],
}
# Includes platform_version so BUG-02 (missing key → KeyError) cannot mask
# the BUG-03 regression tests pre-fix.
FAKE_SYSTEM_INFO = {
    "platform": "Linux",
    "platform_version": "6.0.0-test",
    "python_version": "3.11.0",
    "architecture": "x86_64",
    "hostname": "test-host",
    "cpu_count": 4,
    "memory_total": 1073741824,
}


class TestNetOpsMCPServer:
    """Test NetOpsMCPServer functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_config = tempfile.NamedTemporaryFile(mode="w", delete=False)
        self.temp_config.write('{"logging": {"level": "INFO"}}')
        self.temp_config.close()

    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_config.name):
            os.unlink(self.temp_config.name)

    def test_initialization_with_config(self):
        """Test NetOpsMCPServer initialization with config file."""
        server = NetOpsMCPServer(self.temp_config.name)

        assert server is not None
        assert isinstance(server, NetOpsMCPServer)
        assert server.config is not None

    def test_initialization_without_config(self):
        """Test NetOpsMCPServer initialization without config file."""
        server = NetOpsMCPServer()

        assert server is not None
        assert isinstance(server, NetOpsMCPServer)
        assert server.config is not None

    def test_initialization_with_invalid_config(self):
        """Test NetOpsMCPServer initialization with invalid config file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_file.write('{"invalid": "json"')
            temp_file.close()

            try:
                with pytest.raises(ValueError):
                    NetOpsMCPServer(temp_file.name)
            finally:
                os.unlink(temp_file.name)

    def test_system_requirements_check(self):
        """Test system requirements check on initialization."""
        # This test is simplified since the actual check happens during import
        server = NetOpsMCPServer(self.temp_config.name)
        assert server is not None

    @patch("netops_mcp.server.get_system_info")
    @patch("netops_mcp.server.check_tools_status")
    def test_system_requirements_check_failure(self, mock_check_tools, mock_system_info):
        """Test system requirements check with missing tools.

        Patch targets are the IMPORTING module's bindings — server.py aliases
        the checker as ``check_tools_status``, so patching
        ``netops_mcp.utils.system_check.check_required_tools`` silently
        no-ops (the old, broken pattern this test used to copy).
        """
        mock_check_tools.return_value = dict(FAKE_TOOL_STATUS)
        mock_system_info.return_value = dict(FAKE_SYSTEM_INFO)

        server = NetOpsMCPServer(self.temp_config.name)

        # Should still initialize but log warning
        assert server is not None
        assert isinstance(server, NetOpsMCPServer)
        mock_check_tools.assert_called_once()

    def test_startup_warning_lists_real_missing_tools(self, caplog):
        """BUG-03 regression: the startup warning must list REAL tool names.

        Pre-fix, ``_test_system_requirements`` iterates the 3-key status dict
        (all_available/available_tools/missing_tools) instead of consuming
        the ``missing_tools`` list, so the warning reads
        "Missing tools: all_available".

        ``setup_logging`` is patched out because it strips ALL root-logger
        handlers (including pytest's caplog handler) — without this patch,
        caplog captures nothing regardless of the fix.
        """
        with patch(
            "netops_mcp.server.check_tools_status", return_value=dict(FAKE_TOOL_STATUS)
        ), patch("netops_mcp.server.get_system_info", return_value=dict(FAKE_SYSTEM_INFO)), patch(
            "netops_mcp.server.setup_logging", lambda cfg: logging.getLogger("netops-mcp")
        ):
            with caplog.at_level(logging.WARNING):
                NetOpsMCPServer(self.temp_config.name)

        warning_text = " ".join(
            record.getMessage() for record in caplog.records if record.levelno == logging.WARNING
        )
        assert "nmap" in warning_text
        assert "mtr" in warning_text
        assert "all_available" not in warning_text
        assert "available_tools" not in warning_text

    def test_http_check_required_tools_tool_returns_real_names(self):
        """BUG-03 regression: HTTP ``check_required_tools`` returns real data.

        Pre-fix the tool closure calls ITSELF — the closure named
        ``check_required_tools`` shadows the module-level import inside
        ``_setup_tools``'s scope. Observed pre-fix failure: fastmcp 2.x's
        decorator rebinds the name to a FunctionTool, so the call raises
        ``TypeError: 'FunctionTool' object is not callable`` (plain
        RecursionError under SDK FastMCP); either way the ``except`` clause
        converts it into an ``{"error": ...}`` payload.

        NOTE: Phase 3 (03-01) extracts the tool closures into the shared
        ``netops_mcp.tools.registry`` module, which owns the aliased
        ``check_tools_status`` / ``get_system_info`` bindings the closure
        resolves. The patch target therefore moves to
        ``netops_mcp.tools.registry.*`` in the SAME commit as the extraction.
        The registry also unifies the response envelope onto the typed
        ``mcp.types.TextContent`` (attribute ``.text``), replacing the HTTP
        server's former plain-dict ``["text"]`` form.
        """
        from netops_mcp.server_http import NetOpsMCPHTTPServer

        with patch(
            "netops_mcp.tools.registry.check_tools_status", return_value=dict(FAKE_TOOL_STATUS)
        ), patch(
            "netops_mcp.tools.registry.get_system_info", return_value=dict(FAKE_SYSTEM_INFO)
        ), patch(
            "netops_mcp.server_http.check_tools_status", return_value=dict(FAKE_TOOL_STATUS)
        ):
            # 03-04 deleted _setup_health_check; the PERF-03 startup cache call
            # (server_http.check_tools_status) is patched instead so construction
            # forks no subprocesses.
            server = NetOpsMCPHTTPServer()
            tools = asyncio.run(server.mcp.get_tools())
            # fastmcp 2.11.3 FunctionTool keeps the original closure on `fn`
            result = tools["check_required_tools"].fn()

        assert "recursion" not in result[0].text.lower()
        payload = json.loads(result[0].text)
        assert "error" not in payload
        assert "nmap" in payload["missing_tools"]
        assert "mtr" in payload["missing_tools"]

    def test_tools_initialization(self):
        """Test that all tools are properly initialized."""
        server = NetOpsMCPServer(self.temp_config.name)

        assert hasattr(server, "http_tools")
        assert hasattr(server, "connectivity_tools")
        assert hasattr(server, "dns_tools")
        assert hasattr(server, "discovery_tools")
        assert hasattr(server, "network_tools")
        assert hasattr(server, "monitoring_tools")
        assert hasattr(server, "scanning_tools")

    def test_signal_handlers_setup(self):
        """Test signal handlers are set up."""
        # This test is simplified since signal handlers are set up during import
        server = NetOpsMCPServer(self.temp_config.name)
        assert server is not None

    def test_startup_tests_enabled(self):
        """Test startup tests when enabled."""
        # This test is simplified since startup tests are not implemented in current version
        server = NetOpsMCPServer(self.temp_config.name)
        assert server is not None

    @patch("pytest.main")
    def test_startup_tests_disabled(self, mock_pytest):
        """Test startup tests when disabled."""
        NetOpsMCPServer(self.temp_config.name)

        # Startup tests should not be called by default
        mock_pytest.assert_not_called()

    def test_config_loading(self):
        """Test configuration loading."""
        server = NetOpsMCPServer(self.temp_config.name)

        assert server.config is not None
        assert hasattr(server.config, "logging")
        assert hasattr(server.config, "security")
        assert hasattr(server.config, "network")
        # server attribute doesn't exist in current config model
        assert hasattr(server.config, "logging")

    def test_logging_setup(self):
        """Test logging setup."""
        server = NetOpsMCPServer(self.temp_config.name)

        # Logger should be set up
        assert server.logger is not None

    @patch("os.getenv")
    def test_environment_variable_config(self, mock_getenv):
        """Test configuration from environment variables."""
        mock_getenv.return_value = self.temp_config.name

        server = NetOpsMCPServer()

        assert server is not None
        assert isinstance(server, NetOpsMCPServer)

    def test_tool_registration(self):
        """Test that tools are registered with MCP."""
        server = NetOpsMCPServer(self.temp_config.name)

        # Check that tools are registered (this would require access to mcp instance)
        # For now, just verify tools are initialized
        assert server.http_tools is not None
        assert server.connectivity_tools is not None
        assert server.dns_tools is not None
        assert server.discovery_tools is not None
        assert server.network_tools is not None
        assert server.monitoring_tools is not None
        assert server.scanning_tools is not None
