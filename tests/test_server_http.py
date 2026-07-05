"""
Tests for the HTTP server module.
"""
import re
from unittest.mock import Mock, patch

import pytest
from fastmcp import FastMCP
from netops_mcp.config.models import Config
from netops_mcp.server_http import NetOpsMCPHTTPServer


class TestNetOpsMCPHTTPServer:
    """Test cases for NetOpsMCPHTTPServer."""

    @patch("netops_mcp.server_http.load_config")
    def test_initialization_with_config_file(self, mock_load_config):
        """Test server initialization with config file path."""
        mock_config = Config()
        mock_load_config.return_value = mock_config

        server = NetOpsMCPHTTPServer(config_path="test_config.json")

        mock_load_config.assert_called_once_with("test_config.json")
        assert server.config == mock_config

    @patch("netops_mcp.server_http.load_config")
    def test_initialization_with_invalid_config_file(self, mock_load_config):
        """Test server initialization with invalid config file."""
        mock_load_config.side_effect = FileNotFoundError("Config file not found")

        # Should handle the error gracefully
        with pytest.raises(FileNotFoundError):
            NetOpsMCPHTTPServer(config_path="nonexistent.json")

    def test_config_validation(self):
        """Test that invalid configs are handled properly."""
        # Test with None config_path
        server = NetOpsMCPHTTPServer(config_path=None)
        assert server.config is not None
        assert isinstance(server.config, Config)

    def test_server_attributes(self):
        """Test that server has all required attributes."""
        server = NetOpsMCPHTTPServer()

        assert hasattr(server, "config")
        assert hasattr(server, "logger")
        assert hasattr(server, "host")
        assert hasattr(server, "port")
        assert hasattr(server, "path")
        assert hasattr(server, "mcp")
        assert hasattr(server, "run")

    def test_tools_initialization(self):
        """Test that all tools are properly initialized."""
        server = NetOpsMCPHTTPServer()

        assert hasattr(server, "http_tools")
        assert hasattr(server, "connectivity_tools")
        assert hasattr(server, "dns_tools")
        assert hasattr(server, "discovery_tools")
        assert hasattr(server, "network_tools")
        assert hasattr(server, "monitoring_tools")
        assert hasattr(server, "scanning_tools")

    def test_mcp_initialization(self):
        """Test that FastMCP is properly initialized."""
        server = NetOpsMCPHTTPServer()

        assert server.mcp is not None
        assert isinstance(server.mcp, FastMCP)

    @patch("netops_mcp.server_http.signal.signal")
    def test_run_server(self, mock_signal):
        """Test server run method."""
        # Opt out of auth so run() exercises the server path, not the
        # fail-fast gate (the gate has its own tests in TestAuthGate).
        config = Config()
        config.security.require_auth = False

        with patch("netops_mcp.server_http.load_config", return_value=config):
            server = NetOpsMCPHTTPServer()

        # REF-07: run() now builds the served app via build_http_app() and drives
        # uvicorn.Server directly (no more self.mcp.run). Stub both so run() does
        # not bind a real port while still exercising the signal/serve path.
        with patch.object(NetOpsMCPHTTPServer, "build_http_app") as mock_build, patch(
            "uvicorn.Config"
        ), patch("uvicorn.Server") as mock_uv_server:
            try:
                server.run()
            except SystemExit:
                pass  # Expected to exit

        # Check that signal handlers were set up
        assert mock_signal.call_count >= 2
        mock_build.assert_called_once()
        mock_uv_server.return_value.run.assert_called_once()

    def test_default_parameters(self):
        """Test server initialization with default parameters."""
        server = NetOpsMCPHTTPServer()

        assert server.host == "0.0.0.0"
        assert server.port == 8815
        assert server.path == "/netops-mcp"

    def test_custom_parameters(self):
        """Test server initialization with custom parameters."""
        server = NetOpsMCPHTTPServer(host="127.0.0.1", port=9000, path="/custom-path")

        assert server.host == "127.0.0.1"
        assert server.port == 9000
        assert server.path == "/custom-path"

    @patch("netops_mcp.server_http.FASTMCP_AVAILABLE", False)
    def test_fastmcp_unavailable(self):
        """Test server initialization when FastMCP is not available."""
        with pytest.raises(RuntimeError, match="FastMCP is not available"):
            NetOpsMCPHTTPServer()

    def test_logger_setup(self):
        """Test that logger is properly set up."""
        server = NetOpsMCPHTTPServer()

        assert server.logger is not None
        assert hasattr(server.logger, "info")
        assert hasattr(server.logger, "error")

    def test_tool_registration(self):
        """Test that tools are registered with the MCP server."""
        server = NetOpsMCPHTTPServer()

        # Check that the mcp object has been initialized
        assert server.mcp is not None

        # The tools are registered in the _setup_tools method which is called in __init__
        # We can't easily test the internal tool registration, but we can verify the setup

    def test_config_inheritance(self):
        """Test that server properly inherits config settings."""
        # Create a custom config
        custom_config = Config()
        custom_config.logging.level = "DEBUG"
        custom_config.security.allow_privileged_commands = True

        # Mock load_config to return our custom config
        with patch("netops_mcp.server_http.load_config", return_value=custom_config):
            server = NetOpsMCPHTTPServer(config_path="custom_config.json")

            assert server.config.logging.level == "DEBUG"
            assert server.config.security.allow_privileged_commands is True

    def test_error_handling(self):
        """Test error handling during server initialization."""
        # Test with invalid config that would cause issues
        with patch("netops_mcp.server_http.load_config") as mock_load_config:
            mock_load_config.side_effect = RuntimeError("Config error")

            # Should handle the error gracefully
            with pytest.raises(RuntimeError, match="Config error"):
                NetOpsMCPHTTPServer()

    def test_main_function(self):
        """Test the main function entry point."""
        # This is a basic test to ensure the main function exists and can be called
        from netops_mcp.server_http import main

        # Mock argparse to avoid actual argument parsing
        with patch("argparse.ArgumentParser") as mock_parser:
            mock_args = Mock()
            mock_args.host = "127.0.0.1"
            mock_args.port = 8000
            mock_args.path = "/test"
            mock_args.config = None
            mock_parser.return_value.parse_args.return_value = mock_args

            # Mock the server creation to avoid actually starting it
            with patch("netops_mcp.server_http.NetOpsMCPHTTPServer") as mock_server_class, patch(
                "netops_mcp.server_http.os.getenv", return_value=None
            ):
                mock_server = Mock()
                mock_server_class.return_value = mock_server

                # Call main function
                main()

                # CLI args pass straight through (None-sentinel precedence
                # resolves inside __init__); --config falls back to
                # $NETOPS_MCP_CONFIG (None here — env cleared for the test).
                mock_server_class.assert_called_once_with(
                    config_path=None, host="127.0.0.1", port=8000, path="/test"
                )


class TestAuthGate:
    """Fail-fast auth gate in run() (SEC-01, D-01).

    Default config ships require_auth=True with no api_keys; HTTP mode must
    refuse to start BEFORE uvicorn binds, with operator guidance. Construction
    stays permissive — the gate lives in run(), never in __init__.
    """

    @patch("netops_mcp.server_http.signal.signal")
    def test_gate_blocks_run_without_keys(self, mock_signal):
        """Default config (require_auth=True, empty api_keys) must refuse to run."""
        server = NetOpsMCPHTTPServer()

        # The gate raises BEFORE the served app is built; build_http_app must
        # never be reached (REF-07: no app is served when the gate blocks).
        with patch.object(NetOpsMCPHTTPServer, "build_http_app") as mock_build:
            with pytest.raises(RuntimeError):
                server.run()

        mock_build.assert_not_called()

    @patch("netops_mcp.server_http.signal.signal")
    def test_gate_message_operator_guidance(self, mock_signal):
        """Gate error carries a CSPRNG example key, its sha256: digest and opt-out."""
        server = NetOpsMCPHTTPServer()

        with patch.object(NetOpsMCPHTTPServer, "build_http_app"):
            with pytest.raises(RuntimeError) as excinfo:
                server.run()

        message = str(excinfo.value)
        # A fresh secrets.token_urlsafe(32) example is 43 url-safe base64 chars
        assert re.search(r"[A-Za-z0-9_-]{43}", message)
        assert "sha256:" in message
        assert '"require_auth": false' in message

    @patch("netops_mcp.server_http.signal.signal")
    def test_gate_open_when_auth_disabled(self, mock_signal):
        """Explicit require_auth=False opt-out lets run() reach the served app."""
        config = Config()
        config.security.require_auth = False

        with patch("netops_mcp.server_http.load_config", return_value=config):
            server = NetOpsMCPHTTPServer()

        with patch.object(NetOpsMCPHTTPServer, "build_http_app") as mock_build, patch(
            "uvicorn.Config"
        ), patch("uvicorn.Server") as mock_uv_server:
            try:
                server.run()
            except SystemExit:
                pass

        mock_build.assert_called_once()
        mock_uv_server.return_value.run.assert_called_once()

    @patch("netops_mcp.server_http.signal.signal")
    def test_gate_open_with_hashed_key(self, mock_signal):
        """A configured sha256:<64-hex> key satisfies the gate."""
        config = Config()
        config.security.api_keys = ["sha256:" + "a" * 64]

        with patch("netops_mcp.server_http.load_config", return_value=config):
            server = NetOpsMCPHTTPServer()

        with patch.object(NetOpsMCPHTTPServer, "build_http_app") as mock_build, patch(
            "uvicorn.Config"
        ), patch("uvicorn.Server") as mock_uv_server:
            try:
                server.run()
            except SystemExit:
                pass

        mock_build.assert_called_once()
        mock_uv_server.return_value.run.assert_called_once()

    def test_construction_never_raises(self):
        """Bare construction under default (auth-on, keyless) config must not raise."""
        server = NetOpsMCPHTTPServer()

        assert server.config.security.require_auth is True
        assert server.config.security.api_keys == []

    def test_build_http_app_fails_safe_without_keys(self):
        """WR-01: build_http_app itself refuses to serve fail-open.

        The enforcement invariant travels WITH the served app, not only run()'s
        startup gate. A caller that bypasses run() (e.g. the E2E harness) and
        builds the app under the shipped default (require_auth=True, no keys)
        gets a loud RuntimeError instead of a silently unauthenticated app.
        """
        server = NetOpsMCPHTTPServer()

        assert server.config.security.require_auth is True
        assert server.config.security.api_keys == []
        with pytest.raises(RuntimeError, match="require_auth"):
            server.build_http_app()

    def test_build_http_app_ok_with_hashed_key(self):
        """WR-01: with a configured key, build_http_app returns a served app."""
        config = Config()
        config.security.api_keys = ["sha256:" + "a" * 64]

        with patch("netops_mcp.server_http.load_config", return_value=config):
            server = NetOpsMCPHTTPServer()

        # Must not raise; the auth middleware is attached to the served app.
        app = server.build_http_app()
        middleware_classes = [m.cls for m in app.user_middleware]
        from netops_mcp.middleware.auth import AuthenticationMiddleware

        assert AuthenticationMiddleware in middleware_classes


class TestPrecedence:
    """CLI > config.server > builtin precedence (SEC-08, D-03).

    Builtin defaults (no config, no args → 0.0.0.0/8815//netops-mcp) are
    covered by TestNetOpsMCPHTTPServer.test_default_parameters — not
    duplicated here.
    """

    def _config_with_server(self):
        config = Config()
        config.server.host = "10.9.8.7"
        config.server.port = 9999
        config.server.path = "/custom"
        return config

    def test_config_server_used_when_ctor_omits(self):
        """config.server values win when ctor/CLI omit host/port/path."""
        with patch("netops_mcp.server_http.load_config", return_value=self._config_with_server()):
            server = NetOpsMCPHTTPServer()

        assert server.host == "10.9.8.7"
        assert server.port == 9999
        assert server.path == "/custom"

    def test_ctor_args_win_over_config_server(self):
        """Explicit ctor args beat config.server; omitted ones fall back to it."""
        with patch("netops_mcp.server_http.load_config", return_value=self._config_with_server()):
            server = NetOpsMCPHTTPServer(host="1.2.3.4")

        assert server.host == "1.2.3.4"
        assert server.port == 9999
        assert server.path == "/custom"

    def test_main_config_env_fallback(self):
        """--config omitted falls back to NETOPS_MCP_CONFIG (stdio parity)."""
        from netops_mcp.server_http import main

        with patch("argparse.ArgumentParser") as mock_parser:
            mock_args = Mock()
            mock_args.host = None
            mock_args.port = None
            mock_args.path = None
            mock_args.config = None
            mock_parser.return_value.parse_args.return_value = mock_args

            with patch(
                "netops_mcp.server_http.NetOpsMCPHTTPServer"
            ) as mock_server_class, patch.dict(
                "os.environ", {"NETOPS_MCP_CONFIG": "/env/config.json"}
            ):
                mock_server = Mock()
                mock_server_class.return_value = mock_server

                main()

                mock_server_class.assert_called_once_with(
                    config_path="/env/config.json", host=None, port=None, path=None
                )
