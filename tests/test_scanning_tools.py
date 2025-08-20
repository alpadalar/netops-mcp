"""
Tests for ScanningTools.
"""

import pytest
from unittest.mock import patch, MagicMock
from netops_mcp.tools.security.scanning_tools import ScanningTools


class TestScanningTools:
    """Test ScanningTools functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scanning_tools = ScanningTools()

    def test_initialization(self):
        """Test ScanningTools initialization."""
        assert self.scanning_tools is not None
        assert isinstance(self.scanning_tools, ScanningTools)

    @pytest.mark.parametrize("host,ports,expected_success", [
        ("google.com", "80,443", True),
        ("8.8.8.8", "22,80,443", True),
        ("192.168.1.1", "1-100", True),
        ("", "80", False),
        (None, "80", False),
    ])
    def test_port_scan_valid_inputs(self, host, ports, expected_success):
        """Test port_scan with valid inputs."""
        with patch.object(self.scanning_tools, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": expected_success,
                "stdout": "Port scan results",
                "stderr": "",
                "return_code": 0 if expected_success else 1
            }
            
            result = self.scanning_tools.port_scan(host, ports)
            
            assert len(result) > 0
            assert result[0].type == "text"
            
            if expected_success:
                assert "Port scan" in result[0].text
            else:
                assert "error" in result[0].text.lower()

    @pytest.mark.parametrize("host,ports", [
        ("google.com", ""),
        ("google.com", None),
        ("google.com", "invalid_ports"),
    ])
    def test_port_scan_invalid_ports(self, host, ports):
        """Test port_scan with invalid ports."""
        with patch.object(self.scanning_tools, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "stdout": "",
                "stderr": "Invalid ports",
                "return_code": 1
            }
            
            result = self.scanning_tools.port_scan(host, ports)
            
            assert len(result) > 0
            assert result[0].type == "text"
            assert "error" in result[0].text.lower()

    @pytest.mark.parametrize("host,ports", [
        ("", "80"),
        (None, "80"),
        ("invalid..host", "80"),
    ])
    def test_port_scan_invalid_host(self, host, ports):
        """Test port_scan with invalid hosts."""
        result = self.scanning_tools.port_scan(host, ports)
        
        assert len(result) > 0
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_port_scan_command_timeout(self):
        """Test port_scan with command timeout."""
        with patch.object(self.scanning_tools, '_execute_command') as mock_execute:
            mock_execute.side_effect = TimeoutError("Command timed out")
            
            result = self.scanning_tools.port_scan("google.com", "80")
            
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
    def test_service_enumeration_valid_inputs(self, host, expected_success):
        """Test service_enumeration with valid inputs."""
        with patch.object(self.scanning_tools, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": expected_success,
                "stdout": "Service enumeration results",
                "stderr": "",
                "return_code": 0 if expected_success else 1
            }
            
            result = self.scanning_tools.service_enumeration(host)
            
            assert len(result) > 0
            assert result[0].type == "text"
            
            if expected_success:
                assert "Service enumeration" in result[0].text
            else:
                assert "error" in result[0].text.lower()

    @pytest.mark.parametrize("host", [
        "",
        None,
        "invalid..host",
    ])
    def test_service_enumeration_invalid_host(self, host):
        """Test service_enumeration with invalid hosts."""
        result = self.scanning_tools.service_enumeration(host)
        
        assert len(result) > 0
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_service_enumeration_command_timeout(self):
        """Test service_enumeration with command timeout."""
        with patch.object(self.scanning_tools, '_execute_command') as mock_execute:
            mock_execute.side_effect = TimeoutError("Command timed out")
            
            result = self.scanning_tools.service_enumeration("google.com")
            
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
            assert self.scanning_tools._validate_host(host) == True
        
        for host in invalid_hosts:
            assert self.scanning_tools._validate_host(host) == False

    @pytest.mark.parametrize("valid_ports,invalid_ports", [
        (["80", "443", "22,80,443", "1-100", "80-443"], 
         ["", None, "invalid_ports", "abc", "999999", "0", "65536"]),
    ])
    def test_validate_ports(self, valid_ports, invalid_ports):
        """Test ports validation."""
        for ports in valid_ports:
            assert self.scanning_tools._validate_ports(ports) == True
        
        for ports in invalid_ports:
            assert self.scanning_tools._validate_ports(ports) == False
