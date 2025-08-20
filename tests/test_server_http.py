"""
Tests for the HTTP server module.
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastmcp import FastMCP
from netops_mcp.server_http import NetOpsMCPHTTPServer
from netops_mcp.config.models import Config


class TestNetOpsMCPHTTPServer:
    """Test cases for NetOpsMCPHTTPServer."""

    @patch('netops_mcp.server_http.load_config')
    def test_initialization_with_config_file(self, mock_load_config):
        """Test server initialization with config file path."""
        mock_config = Config()
        mock_load_config.return_value = mock_config
        
        server = NetOpsMCPHTTPServer(config_path="test_config.json")
        
        mock_load_config.assert_called_once_with("test_config.json")
        assert server.config == mock_config

    @patch('netops_mcp.server_http.load_config')
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
        
        assert hasattr(server, 'config')
        assert hasattr(server, 'logger')
        assert hasattr(server, 'host')
        assert hasattr(server, 'port')
        assert hasattr(server, 'path')
        assert hasattr(server, 'mcp')
        assert hasattr(server, 'run')

    def test_tools_initialization(self):
        """Test that all tools are properly initialized."""
        server = NetOpsMCPHTTPServer()
        
        assert hasattr(server, 'http_tools')
        assert hasattr(server, 'connectivity_tools')
        assert hasattr(server, 'dns_tools')
        assert hasattr(server, 'discovery_tools')
        assert hasattr(server, 'network_tools')
        assert hasattr(server, 'monitoring_tools')
        assert hasattr(server, 'scanning_tools')

    def test_mcp_initialization(self):
        """Test that FastMCP is properly initialized."""
        server = NetOpsMCPHTTPServer()
        
        assert server.mcp is not None
        assert isinstance(server.mcp, FastMCP)

    @patch('netops_mcp.server_http.signal.signal')
    def test_run_server(self, mock_signal):
        """Test server run method."""
        server = NetOpsMCPHTTPServer()
        
        # Mock the mcp.run method to avoid actually starting the server
        with patch.object(server.mcp, 'run') as mock_run:
            try:
                server.run()
            except SystemExit:
                pass  # Expected to exit
        
        # Check that signal handlers were set up
        assert mock_signal.call_count >= 2

    def test_default_parameters(self):
        """Test server initialization with default parameters."""
        server = NetOpsMCPHTTPServer()
        
        assert server.host == "0.0.0.0"
        assert server.port == 8815
        assert server.path == "/netops-mcp"

    def test_custom_parameters(self):
        """Test server initialization with custom parameters."""
        server = NetOpsMCPHTTPServer(
            host="127.0.0.1",
            port=9000,
            path="/custom-path"
        )
        
        assert server.host == "127.0.0.1"
        assert server.port == 9000
        assert server.path == "/custom-path"

    @patch('netops_mcp.server_http.FASTMCP_AVAILABLE', False)
    def test_fastmcp_unavailable(self):
        """Test server initialization when FastMCP is not available."""
        with pytest.raises(RuntimeError, match="FastMCP is not available"):
            NetOpsMCPHTTPServer()

    def test_logger_setup(self):
        """Test that logger is properly set up."""
        server = NetOpsMCPHTTPServer()
        
        assert server.logger is not None
        assert hasattr(server.logger, 'info')
        assert hasattr(server.logger, 'error')

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
        with patch('netops_mcp.server_http.load_config', return_value=custom_config):
            server = NetOpsMCPHTTPServer(config_path="custom_config.json")
            
            assert server.config.logging.level == "DEBUG"
            assert server.config.security.allow_privileged_commands is True

    def test_error_handling(self):
        """Test error handling during server initialization."""
        # Test with invalid config that would cause issues
        with patch('netops_mcp.server_http.load_config') as mock_load_config:
            mock_load_config.side_effect = Exception("Config error")
            
            # Should handle the error gracefully
            with pytest.raises(Exception):
                NetOpsMCPHTTPServer()

    def test_main_function(self):
        """Test the main function entry point."""
        # This is a basic test to ensure the main function exists and can be called
        from netops_mcp.server_http import main
        
        # Mock argparse to avoid actual argument parsing
        with patch('argparse.ArgumentParser') as mock_parser:
            mock_args = Mock()
            mock_args.host = '127.0.0.1'
            mock_args.port = 8000
            mock_args.path = '/test'
            mock_args.config = None
            mock_parser.return_value.parse_args.return_value = mock_args
            
            # Mock the server creation to avoid actually starting it
            with patch('netops_mcp.server_http.NetOpsMCPHTTPServer') as mock_server_class:
                mock_server = Mock()
                mock_server_class.return_value = mock_server
                
                # Call main function
                main()
                
                # Verify server was created with correct arguments
                mock_server_class.assert_called_once_with(
                    config_path=None,
                    host='127.0.0.1',
                    port=8000,
                    path='/test'
                )
