"""
Comprehensive tests for connectivity tools functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from netops_mcp.tools.network.connectivity_tools import ConnectivityTools


class TestConnectivityTools:
    """Test connectivity tools functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.connectivity_tools = ConnectivityTools()

    def test_initialization(self):
        """Test ConnectivityTools initialization."""
        assert self.connectivity_tools is not None
        assert hasattr(self.connectivity_tools, 'logger')
        assert hasattr(self.connectivity_tools, '_execute_command')

    @pytest.mark.parametrize("host", [
        "google.com",
        "8.8.8.8",
        "192.168.1.1",
        "localhost",
        "127.0.0.1"
    ])
    def test_ping_host_valid_hosts(self, host, mock_execute_command, sample_ping_output):
        """Test ping with various valid hosts."""
        mock_execute_command.return_value = sample_ping_output
        
        result = self.connectivity_tools.ping_host(host)
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert host in result[0].text
        assert "ping" in result[0].text.lower()

    def test_ping_host_with_custom_count(self, mock_execute_command, sample_ping_output):
        """Test ping with custom packet count."""
        mock_execute_command.return_value = sample_ping_output
        
        result = self.connectivity_tools.ping_host("google.com", count=10)
        
        assert len(result) == 1
        assert result[0].type == "text"
        # Verify count was passed to command
        mock_execute_command.assert_called_once()
        call_args = mock_execute_command.call_args[0][0]
        assert "-c" in call_args
        assert "10" in call_args

    def test_ping_host_with_timeout(self, mock_execute_command, sample_ping_output):
        """Test ping with custom timeout."""
        mock_execute_command.return_value = sample_ping_output
        
        result = self.connectivity_tools.ping_host("google.com", timeout=30)
        
        assert len(result) == 1
        assert result[0].type == "text"
        # Verify timeout was passed to command
        mock_execute_command.assert_called_once()
        call_args = mock_execute_command.call_args[0][0]
        assert "-W" in call_args
        assert "30" in call_args

    def test_ping_host_invalid_host(self, mock_execute_command):
        """Test ping with invalid host."""
        mock_execute_command.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "ping: invalid-host: Name or service not known",
            "return_code": 2,
            "command": "ping -c 4 -W 10 invalid-host"
        }
        
        result = self.connectivity_tools.ping_host("invalid-host")
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_ping_host_empty_host(self):
        """Test ping with empty host."""
        result = self.connectivity_tools.ping_host("")
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_ping_host_none_host(self):
        """Test ping with None host."""
        result = self.connectivity_tools.ping_host(None)
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_traceroute_path_valid_target(self, mock_execute_command, sample_traceroute_output):
        """Test traceroute with valid target."""
        mock_execute_command.return_value = sample_traceroute_output
        
        result = self.connectivity_tools.traceroute_path("google.com")
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "google.com" in result[0].text
        assert "traceroute" in result[0].text.lower()

    def test_traceroute_path_with_max_hops(self, mock_execute_command, sample_traceroute_output):
        """Test traceroute with custom max hops."""
        mock_execute_command.return_value = sample_traceroute_output
        
        result = self.connectivity_tools.traceroute_path("google.com", max_hops=15)
        
        assert len(result) == 1
        assert result[0].type == "text"
        # Verify max hops was passed to command
        mock_execute_command.assert_called_once()
        call_args = mock_execute_command.call_args[0][0]
        assert "-m" in call_args
        assert "15" in call_args

    def test_traceroute_path_with_timeout(self, mock_execute_command, sample_traceroute_output):
        """Test traceroute with custom timeout."""
        mock_execute_command.return_value = sample_traceroute_output
        
        result = self.connectivity_tools.traceroute_path("google.com", timeout=60)
        
        assert len(result) == 1
        assert result[0].type == "text"
        # Verify timeout was passed to command
        mock_execute_command.assert_called_once()
        call_args = mock_execute_command.call_args[0][0]
        assert "-w" in call_args
        assert "60" in call_args

    def test_traceroute_path_invalid_target(self, mock_execute_command):
        """Test traceroute with invalid target."""
        mock_execute_command.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "traceroute: invalid-target: Name or service not known",
            "return_code": 1,
            "command": "traceroute invalid-target"
        }
        
        result = self.connectivity_tools.traceroute_path("invalid-target")
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_mtr_monitor_valid_target(self, mock_execute_command, sample_mtr_output):
        """Test mtr monitor with valid target."""
        mock_execute_command.return_value = sample_mtr_output
        
        result = self.connectivity_tools.mtr_monitor("google.com")
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "google.com" in result[0].text
        # Check that the result contains the target
        assert "google.com" in result[0].text

    def test_mtr_monitor_with_custom_count(self, mock_execute_command, sample_mtr_output):
        """Test mtr monitor with custom count."""
        mock_execute_command.return_value = sample_mtr_output
        
        result = self.connectivity_tools.mtr_monitor("google.com", count=5)
        
        assert len(result) == 1
        assert result[0].type == "text"
        # Verify count was passed to command
        mock_execute_command.assert_called_once()
        call_args = mock_execute_command.call_args[0][0]
        assert "-c" in call_args
        assert "5" in call_args

    def test_mtr_monitor_with_timeout(self, mock_execute_command, sample_mtr_output):
        """Test mtr monitor with custom timeout."""
        mock_execute_command.return_value = sample_mtr_output
        
        result = self.connectivity_tools.mtr_monitor("google.com", timeout=60)
        
        assert len(result) == 1
        assert result[0].type == "text"
        # Verify timeout was passed to command
        mock_execute_command.assert_called_once()
        call_args = mock_execute_command.call_args[0][0]
        assert "-w" in call_args
        assert "60" in call_args

    def test_mtr_monitor_invalid_target(self, mock_execute_command):
        """Test mtr monitor with invalid target."""
        mock_execute_command.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "mtr: invalid-target: Name or service not known",
            "return_code": 1,
            "command": "mtr -c 10 -w 30 --report invalid-target"
        }
        
        result = self.connectivity_tools.mtr_monitor("invalid-target")
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_telnet_connect_valid_host_port(self, mock_execute_command):
        """Test telnet connect with valid host and port."""
        mock_execute_command.return_value = {
            "success": True,
            "stdout": "Connected to google.com.\nEscape character is '^]'.",
            "stderr": "",
            "return_code": 0,
            "command": "timeout 10 telnet google.com 80"
        }
        
        result = self.connectivity_tools.telnet_connect("google.com", 80)
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "google.com" in result[0].text
        assert "80" in result[0].text

    def test_telnet_connect_with_timeout(self, mock_execute_command):
        """Test telnet connect with custom timeout."""
        mock_execute_command.return_value = {
            "success": True,
            "stdout": "Connected to google.com.\nEscape character is '^]'.",
            "stderr": "",
            "return_code": 0,
            "command": "timeout 30 telnet google.com 80"
        }
        
        result = self.connectivity_tools.telnet_connect("google.com", 80, timeout=30)
        
        assert len(result) == 1
        assert result[0].type == "text"
        # Verify timeout was passed to command
        mock_execute_command.assert_called_once()
        call_args = mock_execute_command.call_args[0][0]
        assert "timeout" in call_args
        assert "30" in call_args

    def test_telnet_connect_invalid_host(self, mock_execute_command):
        """Test telnet connect with invalid host."""
        mock_execute_command.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "telnet: could not resolve invalid-host: Name or service not known",
            "return_code": 1,
            "command": "timeout 10 telnet invalid-host 80"
        }
        
        result = self.connectivity_tools.telnet_connect("invalid-host", 80)
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_telnet_connect_invalid_port(self):
        """Test telnet connect with invalid port."""
        result = self.connectivity_tools.telnet_connect("google.com", 70000)
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_netcat_test_valid_host_port(self, mock_execute_command):
        """Test netcat test with valid host and port."""
        mock_execute_command.return_value = {
            "success": True,
            "stdout": "",
            "stderr": "",
            "return_code": 0,
            "command": "nc -z -w 10 google.com 80"
        }
        
        result = self.connectivity_tools.netcat_test("google.com", 80)
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "google.com" in result[0].text
        assert "80" in result[0].text

    def test_netcat_test_with_timeout(self, mock_execute_command):
        """Test netcat test with custom timeout."""
        mock_execute_command.return_value = {
            "success": True,
            "stdout": "",
            "stderr": "",
            "return_code": 0,
            "command": "nc -z -w 30 google.com 80"
        }
        
        result = self.connectivity_tools.netcat_test("google.com", 80, timeout=30)
        
        assert len(result) == 1
        assert result[0].type == "text"
        # Verify timeout was passed to command
        mock_execute_command.assert_called_once()
        call_args = mock_execute_command.call_args[0][0]
        assert "-w" in call_args
        assert "30" in call_args

    def test_netcat_test_invalid_host(self, mock_execute_command):
        """Test netcat test with invalid host."""
        mock_execute_command.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "nc: getaddrinfo: invalid-host: Name or service not known",
            "return_code": 1,
            "command": "nc -z -w 10 invalid-host 80"
        }
        
        result = self.connectivity_tools.netcat_test("invalid-host", 80)
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_netcat_test_invalid_port(self):
        """Test netcat test with invalid port."""
        result = self.connectivity_tools.netcat_test("google.com", 70000)
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_parse_mtr_output_valid(self):
        """Test mtr output parsing with valid output."""
        mtr_output = """Start: 2025-08-19T15:06:45+0000
HOST: test-host                Loss%   Snt   Last   Avg  Best  Wrst StDev
  1.|-- _gateway                0.0%     3    1.2   1.1   0.9   1.3   0.2
  2.|-- 10.0.0.1                0.0%     3    5.4   5.3   5.1   5.6   0.3
  3.|-- google.com              0.0%     3   15.3  15.4  15.1  15.7   0.3"""
        
        parsed = self.connectivity_tools._parse_mtr_output(mtr_output)
        
        assert parsed["target"] == ""
        assert len(parsed["hops"]) == 3
        assert parsed["hops"][0]["hop"] == 1
        assert parsed["hops"][0]["host"] == "_gateway"
        assert parsed["hops"][0]["loss_percent"] == 0.0
        assert parsed["hops"][1]["hop"] == 2
        assert parsed["hops"][1]["host"] == "10.0.0.1"
        assert parsed["hops"][2]["hop"] == 3
        assert parsed["hops"][2]["host"] == "google.com"

    def test_parse_mtr_output_with_malformed_lines(self):
        """Test mtr output parsing with malformed lines."""
        mtr_output = """Start: 2025-08-19T15:06:45+0000
HOST: test-host                Loss%   Snt   Last   Avg  Best  Wrst StDev
  1.|-- _gateway                0.0%     3    1.2   1.1   0.9   1.3   0.2
  malformed line here
  2.|-- 10.0.0.1                0.0%     3    5.4   5.3   5.1   5.6   0.3
  another malformed line
  3.|-- google.com              0.0%     3   15.3  15.4  15.1  15.7   0.3"""
        
        parsed = self.connectivity_tools._parse_mtr_output(mtr_output)
        
        assert parsed["target"] == ""
        assert len(parsed["hops"]) == 3  # Should skip malformed lines
        assert parsed["hops"][0]["hop"] == 1
        assert parsed["hops"][1]["hop"] == 2
        assert parsed["hops"][2]["hop"] == 3

    def test_parse_mtr_output_empty(self):
        """Test mtr output parsing with empty output."""
        parsed = self.connectivity_tools._parse_mtr_output("")
        
        assert parsed["target"] == ""
        assert len(parsed["hops"]) == 0

    def test_parse_mtr_output_only_headers(self):
        """Test mtr output parsing with only header lines."""
        mtr_output = """Start: 2025-08-19T15:06:45+0000
HOST: test-host                Loss%   Snt   Last   Avg  Best  Wrst StDev"""
        
        parsed = self.connectivity_tools._parse_mtr_output(mtr_output)
        
        assert parsed["target"] == ""
        assert len(parsed["hops"]) == 0

    def test_validate_host(self, valid_hosts, invalid_hosts):
        """Test host validation."""
        # Test valid hosts
        for host in valid_hosts:
            assert self.connectivity_tools._validate_host(host) == True
        
        # Test invalid hosts
        for host in invalid_hosts:
            assert self.connectivity_tools._validate_host(host) == False

    def test_validate_port(self, valid_ports, invalid_ports):
        """Test port validation."""
        # Test valid ports
        for port in valid_ports:
            assert self.connectivity_tools._validate_port(port) == True
        
        # Test invalid ports
        for port in invalid_ports:
            assert self.connectivity_tools._validate_port(port) == False

    def test_handle_connectivity_error(self):
        """Test connectivity error handling."""
        error = Exception("Connection failed")
        
        result = self.connectivity_tools._handle_error("ping", error)
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()
        assert "ping" in result[0].text

    def test_command_execution_error_handling(self, mock_execute_command):
        """Test error handling when command execution fails."""
        mock_execute_command.side_effect = Exception("Command execution failed")
        
        result = self.connectivity_tools.ping_host("google.com")
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_timeout_handling(self, mock_execute_command):
        """Test timeout handling in connectivity tools."""
        mock_execute_command.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "Operation timed out",
            "return_code": -1,
            "command": "ping -c 4 -W 10 google.com"
        }
        
        result = self.connectivity_tools.ping_host("google.com", timeout=5)
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "timeout" in result[0].text.lower() or "error" in result[0].text.lower()

    @pytest.mark.parametrize("tool_name,method_name", [
        ("ping", "ping_host"),
        ("traceroute", "traceroute_path"),
        ("mtr", "mtr_monitor"),
        ("telnet", "telnet_connect"),
        ("nc", "netcat_test")
    ])
    def test_tool_methods_exist(self, tool_name, method_name):
        """Test that all expected tool methods exist."""
        assert hasattr(self.connectivity_tools, method_name)
        method = getattr(self.connectivity_tools, method_name)
        assert callable(method)

    def test_format_response_structure(self, mock_execute_command, sample_ping_output):
        """Test that format_response returns correct structure."""
        mock_execute_command.return_value = sample_ping_output
        
        result = self.connectivity_tools.ping_host("google.com")
        
        assert len(result) == 1
        assert hasattr(result[0], 'type')
        assert hasattr(result[0], 'text')
        assert result[0].type == "text"
        assert isinstance(result[0].text, str)
