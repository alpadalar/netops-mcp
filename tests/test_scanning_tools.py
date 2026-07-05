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
        (["80", "443", "22,80,443", "1-100", "80-443", "1-1000"],
         ["", None, "invalid_ports", "abc", "999999", "0", "65536"]),
    ])
    def test_validate_ports(self, valid_ports, invalid_ports):
        """Test ports validation (REF-02: delegates to central validate_port_range)."""
        for ports in valid_ports:
            assert self.scanning_tools._validate_ports(ports) == True

        for ports in invalid_ports:
            assert self.scanning_tools._validate_ports(ports) == False

    def test_port_scan_loopback_target_blocked(self):
        """SEC-03: a loopback target is SSRF-blocked before any scan runs."""
        with patch.object(self.scanning_tools, '_execute_command') as mock_execute:
            result = self.scanning_tools.port_scan("127.0.0.1", "80")

            assert len(result) > 0
            assert "error" in result[0].text.lower()
            mock_execute.assert_not_called()

    def test_service_enumeration_loopback_target_blocked(self):
        """SEC-03: service_enumeration blocks a loopback target."""
        with patch.object(self.scanning_tools, '_execute_command') as mock_execute:
            result = self.scanning_tools.service_enumeration("127.0.0.1")

            assert len(result) > 0
            assert "error" in result[0].text.lower()
            mock_execute.assert_not_called()

    def test_port_scan_global_target_proceeds(self):
        """SEC-03: a global IP target passes the SSRF classifier and proceeds."""
        with patch.object(self.scanning_tools, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "Port scan results",
                "stderr": "",
                "return_code": 0
            }

            result = self.scanning_tools.port_scan("8.8.8.8", "22,80,443")

            assert "Port scan" in result[0].text
            mock_execute.assert_called_once()

    def test_port_scan_and_enum_not_privileged_gated(self):
        """port_scan (-sT) and service_enumeration (-sV -sC) are connect scans
        and must NEVER be privileged-gated, even under the default config."""
        with patch.object(self.scanning_tools, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "results",
                "stderr": "",
                "return_code": 0
            }

            r1 = self.scanning_tools.port_scan("8.8.8.8", "80")
            r2 = self.scanning_tools.service_enumeration("8.8.8.8")

            assert "disabled by config" not in r1[0].text.lower()
            assert "disabled by config" not in r2[0].text.lower()
            assert mock_execute.call_count == 2

    # ------------------------------------------------------------------
    # CR-01: nmap range/CIDR targets must not bypass the SSRF block via the
    # resolver fail-open path. Every covered address is classified before any
    # scan runs; loopback/link-local/metadata ranges are blocked, legitimate
    # private ranges are still allowed (no over-block).
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("target,ports", [
        ("127.0.0.1-10", "1-100"),      # octet range over loopback
        ("127.0.0.0/8", "80"),          # CIDR loopback
        ("169.254.0.0/16", "80"),       # CIDR link-local (incl. IMDS)
        ("169.254.169.250-254", "80"),  # octet range over metadata
    ])
    def test_port_scan_range_cidr_blocked_when_sensitive(self, target, ports):
        """Loopback / link-local / metadata range & CIDR scan targets are blocked
        before _execute_command (the octet-range fail-open bypass is closed)."""
        with patch.object(self.scanning_tools, '_execute_command') as mock_execute:
            result = self.scanning_tools.port_scan(target, ports)

            assert "error" in result[0].text.lower()
            mock_execute.assert_not_called()

    @pytest.mark.parametrize("target,ports", [
        ("192.168.1.0/24", "80"),   # private CIDR
        ("10.0.0.1-50", "80"),      # private octet range
        ("192.168.1.*", "80"),      # private wildcard octet
    ])
    def test_port_scan_private_range_allowed(self, target, ports):
        """Legitimate private range/CIDR scan targets are NOT over-blocked and
        reach the scan subprocess."""
        with patch.object(self.scanning_tools, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "Port scan results",
                "stderr": "",
                "return_code": 0
            }

            result = self.scanning_tools.port_scan(target, ports)

            assert "Port scan" in result[0].text
            mock_execute.assert_called_once()

    def test_service_enumeration_metadata_octet_range_blocked(self):
        """service_enumeration blocks an octet range that covers the IMDS."""
        with patch.object(self.scanning_tools, '_execute_command') as mock_execute:
            result = self.scanning_tools.service_enumeration("169.254.169.250-254")

            assert "error" in result[0].text.lower()
            mock_execute.assert_not_called()
