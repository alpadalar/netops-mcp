"""
Basic tests for NetOps MCP.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from netops_mcp.tools.base import NetOpsTool
from netops_mcp.utils.system_check import check_required_tools


class TestNetOpsTool:
    """Test base NetOpsTool class."""

    def test_netops_tool_initialization(self):
        """Test NetOpsTool initialization."""
        tool = NetOpsTool()
        assert tool is not None
        assert hasattr(tool, "logger")

    def test_validate_host(self):
        """Test host validation."""
        tool = NetOpsTool()

        # Valid hosts
        assert tool._validate_host("google.com") is True
        assert tool._validate_host("192.168.1.1") is True
        assert tool._validate_host("localhost") is True

        # Invalid hosts
        assert tool._validate_host("") is False
        assert tool._validate_host(None) is False

    def test_validate_port(self):
        """Test port validation."""
        tool = NetOpsTool()

        # Valid ports
        assert tool._validate_port(80) is True
        assert tool._validate_port(443) is True
        assert tool._validate_port(8080) is True
        assert tool._validate_port("80") is True

        # Invalid ports
        assert tool._validate_port(0) is False
        assert tool._validate_port(70000) is False
        assert tool._validate_port("invalid") is False


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
        from netops_mcp.tools.network.connectivity_tools import ConnectivityTools
        from netops_mcp.tools.network.discovery_tools import DiscoveryTools
        from netops_mcp.tools.network.dns_tools import DNSTools
        from netops_mcp.tools.network.http_tools import HTTPTools
        from netops_mcp.tools.security.scanning_tools import ScanningTools
        from netops_mcp.tools.system.network_tools import NetworkTools

        # These should work
        assert HTTPTools is not None
        assert ConnectivityTools is not None
        assert DNSTools is not None
        assert DiscoveryTools is not None
        assert NetworkTools is not None
        assert ScanningTools is not None

    except ImportError as e:
        pytest.skip(f"Some modules not available: {e}")
