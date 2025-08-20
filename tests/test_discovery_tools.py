"""
Tests for DiscoveryTools.
"""

import pytest
from unittest.mock import patch, MagicMock
from netops_mcp.tools.network.discovery_tools import DiscoveryTools


class TestDiscoveryTools:
    """Test DiscoveryTools functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.discovery_tools = DiscoveryTools()

    def test_initialization(self):
        """Test DiscoveryTools initialization."""
        assert self.discovery_tools is not None
        assert isinstance(self.discovery_tools, DiscoveryTools)

    @pytest.mark.parametrize("host,scan_type,expected_success", [
        ("google.com", "basic", True),
        ("8.8.8.8", "quick", True),
        ("192.168.1.1", "full", True),
        ("", "basic", False),
        (None, "basic", False),
    ])
    def test_nmap_scan_valid_inputs(self, host, scan_type, expected_success):
        """Test nmap_scan with valid inputs."""
        with patch.object(self.discovery_tools, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": expected_success,
                "stdout": "Nmap scan report for test-host",
                "stderr": "",
                "return_code": 0 if expected_success else 1
            }
            
            result = self.discovery_tools.nmap_scan(host, scan_type=scan_type)
            
            assert len(result) > 0
            assert result[0].type == "text"
            
            if expected_success:
                assert "Nmap scan report" in result[0].text
            else:
                assert "error" in result[0].text.lower()

    @pytest.mark.parametrize("host,scan_type", [
        ("google.com", "invalid_scan_type"),
        ("google.com", ""),
        ("google.com", None),
    ])
    def test_nmap_scan_invalid_scan_type(self, host, scan_type):
        """Test nmap_scan with invalid scan types."""
        result = self.discovery_tools.nmap_scan(host, scan_type=scan_type)
        
        assert len(result) > 0
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    @pytest.mark.parametrize("host,scan_type", [
        ("", "basic"),
        (None, "basic"),
        ("invalid..host", "basic"),
    ])
    def test_nmap_scan_invalid_host(self, host, scan_type):
        """Test nmap_scan with invalid hosts."""
        result = self.discovery_tools.nmap_scan(host, scan_type=scan_type)
        
        assert len(result) > 0
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_nmap_scan_command_timeout(self):
        """Test nmap_scan with command timeout."""
        with patch.object(self.discovery_tools, '_execute_command') as mock_execute:
            mock_execute.side_effect = TimeoutError("Command timed out")
            
            result = self.discovery_tools.nmap_scan("google.com", scan_type="basic")
            
            assert len(result) > 0
            assert result[0].type == "text"
            assert "error" in result[0].text.lower()

    @pytest.mark.parametrize("host,expected_success", [
        ("google.com", True),
        ("8.8.8.8", True),
        ("192.168.1.1", True),
        ("", False),
        (None, False),
    ])
    def test_service_discovery_valid_inputs(self, host, expected_success):
        """Test service_discovery with valid inputs."""
        with patch.object(self.discovery_tools, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": expected_success,
                "stdout": "Service discovery results",
                "stderr": "",
                "return_code": 0 if expected_success else 1
            }
            
            result = self.discovery_tools.service_discovery(host)
            
            assert len(result) > 0
            assert result[0].type == "text"
            
            if expected_success:
                assert "Service discovery" in result[0].text
            else:
                assert "error" in result[0].text.lower()

    @pytest.mark.parametrize("host", [
        "",
        None,
        "invalid..host",
    ])
    def test_service_discovery_invalid_host(self, host):
        """Test service_discovery with invalid hosts."""
        result = self.discovery_tools.service_discovery(host)
        
        assert len(result) > 0
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_service_discovery_command_timeout(self):
        """Test service_discovery with command timeout."""
        with patch.object(self.discovery_tools, '_execute_command') as mock_execute:
            mock_execute.side_effect = TimeoutError("Command timed out")
            
            result = self.discovery_tools.service_discovery("google.com")
            
            assert len(result) > 0
            assert result[0].type == "text"
            assert "error" in result[0].text.lower()

    @pytest.mark.parametrize("valid_hosts,invalid_hosts", [
        (["google.com", "8.8.8.8", "192.168.1.1"], 
         ["", None, "invalid..host", "host with spaces"]),
    ])
    def test_validate_host(self, valid_hosts, invalid_hosts):
        """Test host validation."""
        for host in valid_hosts:
            assert self.discovery_tools._validate_host(host) == True
        
        for host in invalid_hosts:
            assert self.discovery_tools._validate_host(host) == False

    @pytest.mark.parametrize("valid_scan_types,invalid_scan_types", [
        (["basic", "quick", "full"], 
         ["", None, "invalid_type", "custom_scan"]),
    ])
    def test_validate_scan_type(self, valid_scan_types, invalid_scan_types):
        """Test scan type validation."""
        for scan_type in valid_scan_types:
            assert self.discovery_tools._validate_scan_type(scan_type) == True
        
        for scan_type in invalid_scan_types:
            assert self.discovery_tools._validate_scan_type(scan_type) == False
