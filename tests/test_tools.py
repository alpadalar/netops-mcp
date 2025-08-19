"""
Tests for DevOps MCP tools.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from netops_mcp.tools.network.http_tools import HTTPTools
from netops_mcp.tools.network.connectivity_tools import ConnectivityTools
from netops_mcp.tools.network.dns_tools import DNSTools
from netops_mcp.tools.system.network_tools import NetworkTools
from netops_mcp.tools.system.monitoring_tools import MonitoringTools
from netops_mcp.utils.system_check import check_required_tools, get_system_info


class TestHTTPTools:
    """Test HTTP tools functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.http_tools = HTTPTools()

    def test_curl_request_valid_url(self):
        """Test curl request with valid URL."""
        with patch.object(self.http_tools, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": '{"http_code": "200", "time_total": "0.1"}',
                "stderr": "",
                "return_code": 0,
                "command": "curl -s -w @- -o /tmp/curl_output -X GET https://example.com"
            }
            
            result = self.http_tools.curl_request("https://example.com")
            
            assert len(result) == 1
            assert result[0].type == "text"
            assert "https://example.com" in result[0].text

    def test_curl_request_invalid_url(self):
        """Test curl request with invalid URL."""
        result = self.http_tools.curl_request("")
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "error" in result[0].text


class TestConnectivityTools:
    """Test connectivity tools functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.connectivity_tools = ConnectivityTools()

    def test_ping_host_valid(self):
        """Test ping with valid host."""
        with patch.object(self.connectivity_tools, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "PING google.com (142.250.185.78) 56(84) bytes of data.\n64 bytes from google.com: icmp_seq=1 time=1.23 ms",
                "stderr": "",
                "return_code": 0,
                "command": "ping -c 4 -W 10 google.com"
            }
            
            result = self.connectivity_tools.ping_host("google.com")
            
            assert len(result) == 1
            assert result[0].type == "text"
            assert "google.com" in result[0].text

    def test_ping_host_invalid(self):
        """Test ping with invalid host."""
        result = self.connectivity_tools.ping_host("")
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "error" in result[0].text


class TestDNSTools:
    """Test DNS tools functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.dns_tools = DNSTools()

    def test_nslookup_query_valid(self):
        """Test nslookup with valid domain."""
        with patch.object(self.dns_tools, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "Server: 8.8.8.8\nAddress: 8.8.8.8#53\n\nNon-authoritative answer:\nName: google.com\nAddress: 142.250.185.78",
                "stderr": "",
                "return_code": 0,
                "command": "nslookup -type=A google.com"
            }
            
            result = self.dns_tools.nslookup_query("google.com")
            
            assert len(result) == 1
            assert result[0].type == "text"
            assert "google.com" in result[0].text


class TestNetworkTools:
    """Test network tools functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.network_tools = NetworkTools()

    def test_ss_connections(self):
        """Test ss connections command."""
        with patch.object(self.network_tools, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "State      Recv-Q Send-Q Local Address:Port               Peer Address:Port\nLISTEN     0      128     *:22                  *:*",
                "stderr": "",
                "return_code": 0,
                "command": "ss -tuln"
            }
            
            result = self.network_tools.ss_connections()
            
            assert len(result) == 1
            assert result[0].type == "text"
            assert "LISTEN" in result[0].text


class TestMonitoringTools:
    """Test monitoring tools functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.monitoring_tools = MonitoringTools()

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_system_status(self, mock_disk, mock_memory, mock_cpu):
        """Test system status command."""
        mock_cpu.return_value = 25.5
        mock_memory.return_value = MagicMock(
            total=8589934592,  # 8GB
            available=4294967296,  # 4GB
            used=4294967296,  # 4GB
            percent=50.0
        )
        mock_disk.return_value = MagicMock(
            total=107374182400,  # 100GB
            used=53687091200,  # 50GB
            free=53687091200  # 50GB
        )
        
        result = self.monitoring_tools.system_status()
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "cpu" in result[0].text
        assert "memory" in result[0].text


class TestSystemCheck:
    """Test system check utilities."""

    def test_check_required_tools(self):
        """Test required tools check."""
        tools = check_required_tools()
        
        assert isinstance(tools, dict)
        assert "curl" in tools
        assert "ping" in tools
        assert "nmap" in tools

    def test_get_system_info(self):
        """Test system info retrieval."""
        info = get_system_info()
        
        assert isinstance(info, dict)
        assert "platform" in info
        assert "python_version" in info
        assert "cpu_count" in info
