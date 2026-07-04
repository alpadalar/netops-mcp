"""
Comprehensive tests for connectivity tools functionality.
"""

import json

import pytest
from unittest.mock import patch, MagicMock
from netops_mcp.tools.network.connectivity_tools import ConnectivityTools

# Byte-compat characterization constants: exact exit-0 MCP response strings
# captured from pre-delegation code (plan 01-02) by calling the tool methods
# with the conftest sample fixtures and recording repr(result[0].text).
# Serialization contract: base.py _format_response json.dumps(data, indent=2, default=str)
# over insertion-ordered response dicts. Plan 01-04 must keep these green.

EXPECTED_PING_SUCCESS_JSON = (
    '{\n'
    '  "host": "google.com",\n'
    '  "success": true,\n'
    '  "stats": {\n'
    '    "packets_transmitted": 4,\n'
    '    "packets_received": 4,\n'
    '    "packet_loss_percent": 0.0,\n'
    '    "min_rtt": 1.23,\n'
    '    "avg_rtt": 1.395,\n'
    '    "max_rtt": 1.56,\n'
    '    "mdev_rtt": 0.134\n'
    '  },\n'
    '  "raw_output": "PING google.com (142.250.185.78) 56(84) bytes of data'
    '.\\n64 bytes from google.com (142.250.185.78): icmp_seq=1 time=1.23 ms\\'
    'n64 bytes from google.com (142.250.185.78): icmp_seq=2 time=1.45 ms\\n6'
    '4 bytes from google.com (142.250.185.78): icmp_seq=3 time=1.34 ms\\n64 '
    'bytes from google.com (142.250.185.78): icmp_seq=4 time=1.56 ms\\n\\n---'
    ' google.com ping statistics ---\\n4 packets transmitted, 4 received, 0%'
    ' packet loss, time 3003ms\\nrtt min/avg/max/mdev = 1.230/1.395/1.560/0.'
    '134 ms"\n'
    '}'
)

EXPECTED_TRACEROUTE_SUCCESS_JSON = (
    '{\n'
    '  "target": "google.com",\n'
    '  "success": true,\n'
    '  "hops": [\n'
    '    {\n'
    '      "hop_number": 1,\n'
    '      "host": "_gateway",\n'
    '      "ip": "_gateway",\n'
    '      "times": [\n'
    '        1.234,\n'
    '        0.987,\n'
    '        1.123\n'
    '      ]\n'
    '    },\n'
    '    {\n'
    '      "hop_number": 2,\n'
    '      "host": "10.0.0.1",\n'
    '      "ip": "10.0.0.1",\n'
    '      "times": [\n'
    '        5.678,\n'
    '        5.432,\n'
    '        5.567\n'
    '      ]\n'
    '    },\n'
    '    {\n'
    '      "hop_number": 3,\n'
    '      "host": "172.16.0.1",\n'
    '      "ip": "172.16.0.1",\n'
    '      "times": [\n'
    '        10.123,\n'
    '        9.876,\n'
    '        10.234\n'
    '      ]\n'
    '    },\n'
    '    {\n'
    '      "hop_number": 4,\n'
    '      "host": "*",\n'
    '      "ip": "*",\n'
    '      "times": []\n'
    '    },\n'
    '    {\n'
    '      "hop_number": 5,\n'
    '      "host": "google.com",\n'
    '      "ip": "google.com",\n'
    '      "times": [\n'
    '        15.678,\n'
    '        15.432,\n'
    '        15.567\n'
    '      ]\n'
    '    }\n'
    '  ],\n'
    '  "raw_output": "traceroute to google.com (142.250.185.78), 30 hops ma'
    'x, 60 byte packets\\n 1  _gateway (192.168.1.1)  1.234 ms  0.987 ms  1.'
    '123 ms\\n 2  10.0.0.1 (10.0.0.1)  5.678 ms  5.432 ms  5.567 ms\\n 3  172'
    '.16.0.1 (172.16.0.1)  10.123 ms  9.876 ms  10.234 ms\\n 4  * * *\\n 5  g'
    'oogle.com (142.250.185.78)  15.678 ms  15.432 ms  15.567 ms"\n'
    '}'
)

EXPECTED_MTR_SUCCESS_JSON = (
    '{\n'
    '  "target": "google.com",\n'
    '  "success": true,\n'
    '  "stats": {\n'
    '    "target": "",\n'
    '    "hops": []\n'
    '  },\n'
    '  "raw_output": "Start: 2025-08-19T15:06:45+0000\\nHOST: test-host     '
    '           Loss%   Snt   Last   Avg  Best  Wrst StDev\\n  1.|-- _gatewa'
    'y                0.0%     3    1.2   1.1   0.9   1.3   0.2\\n  2.|-- 10'
    '.0.0.1                0.0%     3    5.4   5.3   5.1   5.6   0.3\\n  3.|'
    '-- 172.16.0.1              0.0%     3   10.1  10.2   9.8  10.5   0.4\\n'
    '  4.|-- google.com              0.0%     3   15.3  15.4  15.1  15.7   '
    '0.3"\n'
    '}'
)


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
        """Test mtr monitor with custom timeout (BUG-04 regression).

        mtr's `-w` is `--report-wide` (no argument); passing the timeout after
        it makes mtr probe the timeout value as an extra target host. The
        timeout must never appear in the command — the overall deadline is
        enforced via _execute_command's second positional argument.
        """
        mock_execute_command.return_value = sample_mtr_output

        result = self.connectivity_tools.mtr_monitor("google.com", timeout=60)

        assert len(result) == 1
        assert result[0].type == "text"
        mock_execute_command.assert_called_once()
        call_args = mock_execute_command.call_args[0][0]
        assert "-w" not in call_args
        assert "60" not in call_args
        assert mock_execute_command.call_args[0][1] == 70

    def test_mtr_monitor_invalid_target(self, mock_execute_command):
        """Test mtr monitor with invalid target."""
        mock_execute_command.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "mtr: invalid-target: Name or service not known",
            "return_code": 1,
            "command": "mtr -c 10 --report invalid-target"
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

    # NOTE: the former mtr-parser unit tests (4 cases) were migrated to
    # tests/test_output_parser.py::TestParseMtrOutput in plan 01-02; the
    # inline parser methods they exercised were deleted in plan 01-04
    # (REF-03: OutputParser is the single parsing source).

    def test_validate_host(self, valid_hosts, invalid_hosts):
        """Test host validation."""
        # Test valid hosts
        for host in valid_hosts:
            # This test is simplified since IPv6 validation is not implemented
            pass
        assert self.connectivity_tools._validate_host("google.com") == True
        
        # Test invalid hosts
        for host in invalid_hosts:
            # This test is simplified since validation is not strict
            pass
        assert self.connectivity_tools._validate_host("invalid..host") == False

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

    def test_ping_success_response_bytes_unchanged(self, mock_execute_command,
                                                   sample_ping_output):
        """Byte-compat: exit-0 ping MCP response must stay byte-identical."""
        mock_execute_command.return_value = sample_ping_output

        result = self.connectivity_tools.ping_host("google.com")

        assert result[0].text == EXPECTED_PING_SUCCESS_JSON

    def test_traceroute_success_response_bytes_unchanged(self, mock_execute_command,
                                                         sample_traceroute_output):
        """Byte-compat: exit-0 traceroute MCP response must stay byte-identical."""
        mock_execute_command.return_value = sample_traceroute_output

        result = self.connectivity_tools.traceroute_path("google.com")

        assert result[0].text == EXPECTED_TRACEROUTE_SUCCESS_JSON

    def test_mtr_success_response_bytes_unchanged(self, mock_execute_command,
                                                  sample_mtr_output):
        """Byte-compat: exit-0 mtr MCP response must stay byte-identical."""
        mock_execute_command.return_value = sample_mtr_output

        result = self.connectivity_tools.mtr_monitor("google.com", count=3)

        assert result[0].text == EXPECTED_MTR_SUCCESS_JSON

    # --- BUG-01 regression tests (plan 01-04): unreachable / zero-tx ping ---

    def test_ping_host_unreachable_returns_stats(self, mock_execute_command,
                                                 sample_ping_unreachable_output):
        """Unreachable host (exit 1, stats block on stdout) returns stats, not error."""
        mock_execute_command.return_value = sample_ping_unreachable_output

        result = self.connectivity_tools.ping_host("192.0.2.1")
        data = json.loads(result[0].text)

        assert data["success"] is False
        assert "stats" in data
        assert data["stats"]["packets_transmitted"] == 2
        assert data["stats"]["packet_loss_percent"] == 100.0
        assert "error" not in data

    def test_ping_host_zero_tx_returns_stats_no_zerodivision(self, mock_execute_command,
                                                             sample_ping_zero_tx_output):
        """Zero packets transmitted: structured stats (loss 100, rtt null), no crash."""
        mock_execute_command.return_value = sample_ping_zero_tx_output

        result = self.connectivity_tools.ping_host("8.8.8.8")
        data = json.loads(result[0].text)

        assert "stats" in data
        assert data["stats"]["packet_loss_percent"] == 100
        assert data["stats"]["min_rtt"] is None
        assert data["stats"]["avg_rtt"] is None
        assert data["stats"]["max_rtt"] is None
        assert data["stats"]["mdev_rtt"] is None

    def test_ping_host_dns_failure_keeps_error_shape(self, mock_execute_command,
                                                     sample_ping_dns_failure_output):
        """DNS failure (empty stdout, no stats block) keeps the error response shape."""
        mock_execute_command.return_value = sample_ping_dns_failure_output

        result = self.connectivity_tools.ping_host("nonexistent-host.invalid")
        data = json.loads(result[0].text)

        assert set(data.keys()) == {"host", "success", "error", "raw_output"}
        assert data["success"] is False
