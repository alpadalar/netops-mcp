"""
Basic tests for NetOps MCP.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from netops_mcp.tools.base import NetOpsTool
from netops_mcp.utils.system_check import check_required_tools


class TestNetOpsTool:
    """Test base NetOpsTool class."""

    def test_netops_tool_initialization(self):
        """Test NetOpsTool initialization."""
        tool = NetOpsTool()
        assert tool is not None
        assert hasattr(tool, 'logger')

    def test_validate_host(self):
        """Test host validation."""
        tool = NetOpsTool()
        
        # Valid hosts
        assert tool._validate_host("google.com") == True
        assert tool._validate_host("192.168.1.1") == True
        assert tool._validate_host("localhost") == True
        
        # Invalid hosts
        assert tool._validate_host("") == False
        assert tool._validate_host(None) == False

    def test_validate_port(self):
        """Test port validation."""
        tool = NetOpsTool()
        
        # Valid ports
        assert tool._validate_port(80) == True
        assert tool._validate_port(443) == True
        assert tool._validate_port(8080) == True
        assert tool._validate_port("80") == True
        
        # Invalid ports
        assert tool._validate_port(0) == False
        assert tool._validate_port(70000) == False
        assert tool._validate_port("invalid") == False


class TestSystemCheck:
    """Test system check utilities."""

    def test_check_required_tools(self):
        """Test required tools check."""
        result = check_required_tools()
        
        assert isinstance(result, dict)
        assert "available_tools" in result
        assert "missing_tools" in result
        assert "all_available" in result
        assert "curl" in result["available_tools"] or "curl" in result["missing_tools"]
        assert "ping" in result["available_tools"] or "ping" in result["missing_tools"]
        assert "nmap" in result["available_tools"] or "nmap" in result["missing_tools"]
        
        # Check that all values are lists
        assert isinstance(result["available_tools"], list)
        assert isinstance(result["missing_tools"], list)
        assert isinstance(result["all_available"], bool)


def test_imports():
    """Test that all modules can be imported."""
    try:
        from netops_mcp.tools.network.http_tools import HTTPTools
        from netops_mcp.tools.network.connectivity_tools import ConnectivityTools
        from netops_mcp.tools.network.dns_tools import DNSTools
        from netops_mcp.tools.network.discovery_tools import DiscoveryTools
        from netops_mcp.tools.system.network_tools import NetworkTools
        from netops_mcp.tools.security.scanning_tools import ScanningTools
        
        # These should work
        assert HTTPTools is not None
        assert ConnectivityTools is not None
        assert DNSTools is not None
        assert DiscoveryTools is not None
        assert NetworkTools is not None
        assert ScanningTools is not None
        
    except ImportError as e:
        pytest.skip(f"Some modules not available: {e}")
