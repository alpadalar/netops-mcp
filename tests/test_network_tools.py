"""
Tests for NetworkTools.
"""

import pytest
from unittest.mock import patch, MagicMock
from netops_mcp.tools.system.network_tools import NetworkTools


class TestNetworkTools:
    """Test NetworkTools functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.network_tools = NetworkTools()

    def test_initialization(self):
        """Test NetworkTools initialization."""
        assert self.network_tools is not None
        assert isinstance(self.network_tools, NetworkTools)

    @pytest.mark.parametrize("expected_success", [True, False])
    def test_ss_connections_valid_inputs(self, expected_success):
        """Test ss_connections with valid inputs."""
        with patch.object(self.network_tools, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": expected_success,
                "stdout": "Socket statistics",
                "stderr": "",
                "return_code": 0 if expected_success else 1
            }
            
            result = self.network_tools.ss_connections()
            
            assert len(result) > 0
            assert result[0].type == "text"
            
            if expected_success:
                assert "Socket statistics" in result[0].text
            else:
                assert '"success": false' in result[0].text

    def test_ss_connections_command_timeout(self):
        """Test ss_connections with command timeout."""
        with patch.object(self.network_tools, '_execute_command') as mock_execute:
            mock_execute.side_effect = TimeoutError("Command timed out")
            
            result = self.network_tools.ss_connections()
            
            assert len(result) > 0
            assert result[0].type == "text"
            assert "error" in result[0].text.lower()

    @pytest.mark.parametrize("expected_success", [True, False])
    def test_netstat_connections_valid_inputs(self, expected_success):
        """Test netstat_connections with valid inputs."""
        with patch.object(self.network_tools, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": expected_success,
                "stdout": "Network statistics",
                "stderr": "",
                "return_code": 0 if expected_success else 1
            }
            
            result = self.network_tools.netstat_connections()
            
            assert len(result) > 0
            assert result[0].type == "text"
            
            if expected_success:
                assert "Network statistics" in result[0].text
            else:
                assert '"success": false' in result[0].text

    def test_netstat_connections_command_timeout(self):
        """Test netstat_connections with command timeout."""
        with patch.object(self.network_tools, '_execute_command') as mock_execute:
            mock_execute.side_effect = TimeoutError("Command timed out")
            
            result = self.network_tools.netstat_connections()
            
            assert len(result) > 0
            assert result[0].type == "text"
            assert "error" in result[0].text.lower()

    @pytest.mark.parametrize("expected_success", [True, False])
    def test_arp_table_valid_inputs(self, expected_success):
        """Test arp_table with valid inputs."""
        with patch.object(self.network_tools, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": expected_success,
                "stdout": "ARP table",
                "stderr": "",
                "return_code": 0 if expected_success else 1
            }
            
            result = self.network_tools.arp_table()
            
            assert len(result) > 0
            assert result[0].type == "text"
            
            if expected_success:
                assert "ARP table" in result[0].text
            else:
                assert '"success": false' in result[0].text

    def test_arp_table_command_timeout(self):
        """Test arp_table with command timeout."""
        with patch.object(self.network_tools, '_execute_command') as mock_execute:
            mock_execute.side_effect = TimeoutError("Command timed out")
            
            result = self.network_tools.arp_table()
            
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
    def test_arping_host_valid_inputs(self, host, expected_success):
        """Test arping_host with valid inputs."""
        with patch.object(self.network_tools, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": expected_success,
                "stdout": "ARP ping results",
                "stderr": "",
                "return_code": 0 if expected_success else 1
            }
            
            result = self.network_tools.arping_host(host)
            
            assert len(result) > 0
            assert result[0].type == "text"
            
            if expected_success:
                assert "ARP ping" in result[0].text
            else:
                # For invalid hosts, we get error format, for failed commands we get success: false
                assert '"success": false' in result[0].text or '"error": true' in result[0].text

    @pytest.mark.parametrize("host", [
        "",
        None,
        "invalid..host",
    ])
    def test_arping_host_invalid_host(self, host):
        """Test arping_host with invalid hosts."""
        result = self.network_tools.arping_host(host)
        
        assert len(result) > 0
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_arping_host_command_timeout(self):
        """Test arping_host with command timeout."""
        with patch.object(self.network_tools, '_execute_command') as mock_execute:
            mock_execute.side_effect = TimeoutError("Command timed out")
            
            result = self.network_tools.arping_host("google.com")
            
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
            assert self.network_tools._validate_host(host) == True
        
        for host in invalid_hosts:
            assert self.network_tools._validate_host(host) == False
