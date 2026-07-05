"""
Tests for DiscoveryTools.
"""

from unittest.mock import patch

import pytest
from netops_mcp.config.models import Config, SecurityConfig
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

    @pytest.mark.parametrize(
        "host,scan_type,expected_success",
        [
            # basic (-sT) is an ungated connect scan; global/private IP targets
            # pass the SSRF classifier. The privileged quick/full cases moved to
            # dedicated gate tests below (they fire before _execute_command).
            ("google.com", "basic", True),
            ("8.8.8.8", "basic", True),
            ("192.168.1.1", "basic", True),
            ("", "basic", False),
            (None, "basic", False),
        ],
    )
    def test_nmap_scan_valid_inputs(self, host, scan_type, expected_success):
        """Test nmap_scan with valid inputs."""
        with patch.object(self.discovery_tools, "_execute_command") as mock_execute:
            mock_execute.return_value = {
                "success": expected_success,
                "stdout": "Nmap scan report for test-host",
                "stderr": "",
                "return_code": 0 if expected_success else 1,
            }

            result = self.discovery_tools.nmap_scan(host, scan_type=scan_type)

            assert len(result) > 0
            assert result[0].type == "text"

            if expected_success:
                assert "Nmap scan report" in result[0].text
            else:
                assert "error" in result[0].text.lower()

    @pytest.mark.parametrize("scan_type", ["quick", "full"])
    def test_nmap_scan_privileged_gated_by_default(self, scan_type):
        """SEC-05: quick (-sS) / full (-sS -O) are denied when
        allow_privileged_commands is False (the default), and the denial
        fires BEFORE _execute_command is ever reached."""
        with patch.object(self.discovery_tools, "_execute_command") as mock_execute:
            result = self.discovery_tools.nmap_scan("8.8.8.8", scan_type=scan_type)

            assert len(result) > 0
            assert result[0].type == "text"
            assert "disabled by config" in result[0].text.lower()
            mock_execute.assert_not_called()

    @pytest.mark.parametrize("scan_type", ["quick", "full"])
    def test_nmap_scan_privileged_allowed_when_flag_true(self, scan_type):
        """SEC-05: with allow_privileged_commands=True the privileged scan
        types proceed to _execute_command."""
        privileged_tools = DiscoveryTools(
            Config(security=SecurityConfig(allow_privileged_commands=True))
        )
        with patch.object(privileged_tools, "_execute_command") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "Nmap scan report for test-host",
                "stderr": "",
                "return_code": 0,
            }

            result = privileged_tools.nmap_scan("8.8.8.8", scan_type=scan_type)

            assert "Nmap scan report" in result[0].text
            assert "disabled by config" not in result[0].text.lower()
            mock_execute.assert_called_once()

    def test_nmap_scan_basic_not_privileged_gated(self):
        """The basic (-sT) connect scan is never privileged-gated, even with
        the default (privileged-off) config."""
        with patch.object(self.discovery_tools, "_execute_command") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "Nmap scan report for test-host",
                "stderr": "",
                "return_code": 0,
            }

            result = self.discovery_tools.nmap_scan("8.8.8.8", scan_type="basic")

            assert "disabled by config" not in result[0].text.lower()
            mock_execute.assert_called_once()

    def test_service_discovery_not_privileged_gated(self):
        """service_discovery (-sV -sC connect scan) is never privileged-gated."""
        with patch.object(self.discovery_tools, "_execute_command") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "Service discovery results",
                "stderr": "",
                "return_code": 0,
            }

            result = self.discovery_tools.service_discovery("8.8.8.8")

            assert "disabled by config" not in result[0].text.lower()
            mock_execute.assert_called_once()

    def test_nmap_scan_loopback_target_blocked(self):
        """SEC-03: a loopback target is SSRF-blocked before any scan runs."""
        with patch.object(self.discovery_tools, "_execute_command") as mock_execute:
            result = self.discovery_tools.nmap_scan("127.0.0.1", scan_type="basic")

            assert len(result) > 0
            assert "error" in result[0].text.lower()
            mock_execute.assert_not_called()

    def test_service_discovery_loopback_target_blocked(self):
        """SEC-03: service_discovery blocks a loopback target."""
        with patch.object(self.discovery_tools, "_execute_command") as mock_execute:
            result = self.discovery_tools.service_discovery("127.0.0.1")

            assert len(result) > 0
            assert "error" in result[0].text.lower()
            mock_execute.assert_not_called()

    def test_nmap_scan_global_target_proceeds(self):
        """SEC-03: a global IP target passes the SSRF classifier and proceeds."""
        with patch.object(self.discovery_tools, "_execute_command") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "Nmap scan report for test-host",
                "stderr": "",
                "return_code": 0,
            }

            result = self.discovery_tools.nmap_scan("8.8.8.8", scan_type="basic")

            assert "Nmap scan report" in result[0].text
            mock_execute.assert_called_once()

    # ------------------------------------------------------------------
    # CR-01: nmap range/CIDR scan targets must not bypass the SSRF block via the
    # resolver fail-open path.
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        "target",
        [
            "169.254.169.250-254",  # octet range over cloud metadata (IMDS)
            "127.0.0.1-10",  # octet range over loopback
            "127.0.0.0/8",  # CIDR loopback
            "169.254.0.0/16",  # CIDR link-local
        ],
    )
    def test_nmap_scan_range_cidr_blocked_when_sensitive(self, target):
        """nmap_scan blocks loopback/link-local/metadata range & CIDR targets
        before _execute_command (octet-range fail-open bypass closed)."""
        with patch.object(self.discovery_tools, "_execute_command") as mock_execute:
            result = self.discovery_tools.nmap_scan(target, scan_type="basic")

            assert "error" in result[0].text.lower()
            mock_execute.assert_not_called()

    @pytest.mark.parametrize(
        "target",
        [
            "192.168.1.0/24",  # private CIDR
            "10.0.0.1-50",  # private octet range
        ],
    )
    def test_nmap_scan_private_range_allowed(self, target):
        """Legitimate private range/CIDR targets are NOT over-blocked."""
        with patch.object(self.discovery_tools, "_execute_command") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "Nmap scan report for test-host",
                "stderr": "",
                "return_code": 0,
            }

            result = self.discovery_tools.nmap_scan(target, scan_type="basic")

            assert "Nmap scan report" in result[0].text
            mock_execute.assert_called_once()

    def test_service_discovery_loopback_octet_range_blocked(self):
        """service_discovery blocks an octet range that covers loopback."""
        with patch.object(self.discovery_tools, "_execute_command") as mock_execute:
            result = self.discovery_tools.service_discovery("127.0.0.1-10")

            assert "error" in result[0].text.lower()
            mock_execute.assert_not_called()

    # ------------------------------------------------------------------
    # WR-02: for a plain hostname the argv handed to nmap must be the pinned
    # resolved IP (classified here), not the name — so nmap cannot independently
    # re-resolve the name to a DNS-rebind target. example.com resolves to the
    # fixed global 93.184.216.34 via the offline conftest SSRF resolver stub.
    # ------------------------------------------------------------------
    def test_nmap_scan_pins_resolved_ip_for_hostname(self):
        """nmap_scan hands nmap the pinned resolved IP, not the hostname."""
        with patch.object(self.discovery_tools, "_execute_command") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "Nmap scan report for test-host",
                "stderr": "",
                "return_code": 0,
            }

            self.discovery_tools.nmap_scan("example.com", scan_type="basic")

            argv = mock_execute.call_args.args[0]
            assert "93.184.216.34" in argv
            assert "example.com" not in argv

    def test_service_discovery_pins_resolved_ip_for_hostname(self):
        """service_discovery hands nmap the pinned resolved IP, not the name."""
        with patch.object(self.discovery_tools, "_execute_command") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "Service discovery results",
                "stderr": "",
                "return_code": 0,
            }

            self.discovery_tools.service_discovery("example.com")

            argv = mock_execute.call_args.args[0]
            assert "93.184.216.34" in argv
            assert "example.com" not in argv

    @pytest.mark.parametrize(
        "target",
        [
            "8.8.8.8",  # single global literal
            "192.168.1.0/24",  # private CIDR
            "10.0.0.1-50",  # private octet range
        ],
    )
    def test_nmap_scan_literal_range_target_not_pinned(self, target):
        """Literal / range / CIDR targets are passed through to nmap unchanged
        (nmap never re-resolves numeric syntax, so there is nothing to pin)."""
        with patch.object(self.discovery_tools, "_execute_command") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "Nmap scan report for test-host",
                "stderr": "",
                "return_code": 0,
            }

            self.discovery_tools.nmap_scan(target, scan_type="basic")

            argv = mock_execute.call_args.args[0]
            assert target in argv

    # ------------------------------------------------------------------
    # IN-01: nmap_scan / service_discovery now gate the ports argument via the
    # central validate_port_range, matching port_scan / service_enumeration.
    # ------------------------------------------------------------------
    def test_nmap_scan_invalid_ports_rejected(self):
        """A malformed ports spec is rejected before nmap runs."""
        with patch.object(self.discovery_tools, "_execute_command") as mock_execute:
            result = self.discovery_tools.nmap_scan("8.8.8.8", ports="bad_ports", scan_type="basic")

            assert "error" in result[0].text.lower()
            mock_execute.assert_not_called()

    def test_service_discovery_invalid_ports_rejected(self):
        """service_discovery rejects a malformed ports spec before nmap runs."""
        with patch.object(self.discovery_tools, "_execute_command") as mock_execute:
            result = self.discovery_tools.service_discovery("8.8.8.8", ports="bad_ports")

            assert "error" in result[0].text.lower()
            mock_execute.assert_not_called()

    @pytest.mark.parametrize("ports", ["22,80,443", "1-1000"])
    def test_nmap_scan_valid_ports_proceed(self, ports):
        """A well-formed ports spec is NOT over-blocked and reaches the scan."""
        with patch.object(self.discovery_tools, "_execute_command") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "Nmap scan report for test-host",
                "stderr": "",
                "return_code": 0,
            }

            result = self.discovery_tools.nmap_scan("8.8.8.8", ports=ports, scan_type="basic")

            assert "Nmap scan report" in result[0].text
            mock_execute.assert_called_once()

    @pytest.mark.parametrize(
        "valid_ports,invalid_ports",
        [
            (
                ["80", "443", "22,80,443", "1-100", "80-443"],
                ["", None, "invalid_ports", "abc", "999999", "0", "65536"],
            ),
        ],
    )
    def test_validate_ports(self, valid_ports, invalid_ports):
        """DiscoveryTools._validate_ports delegates to central validate_port_range."""
        for ports in valid_ports:
            assert self.discovery_tools._validate_ports(ports) is True

        for ports in invalid_ports:
            assert self.discovery_tools._validate_ports(ports) is False

    @pytest.mark.parametrize(
        "host,scan_type",
        [
            ("google.com", "invalid_scan_type"),
            ("google.com", ""),
            ("google.com", None),
        ],
    )
    def test_nmap_scan_invalid_scan_type(self, host, scan_type):
        """Test nmap_scan with invalid scan types."""
        result = self.discovery_tools.nmap_scan(host, scan_type=scan_type)

        assert len(result) > 0
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    @pytest.mark.parametrize(
        "host,scan_type",
        [
            ("", "basic"),
            (None, "basic"),
            ("invalid..host", "basic"),
        ],
    )
    def test_nmap_scan_invalid_host(self, host, scan_type):
        """Test nmap_scan with invalid hosts."""
        result = self.discovery_tools.nmap_scan(host, scan_type=scan_type)

        assert len(result) > 0
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_nmap_scan_command_timeout(self):
        """Test nmap_scan with command timeout."""
        with patch.object(self.discovery_tools, "_execute_command") as mock_execute:
            mock_execute.side_effect = TimeoutError("Command timed out")

            result = self.discovery_tools.nmap_scan("google.com", scan_type="basic")

            assert len(result) > 0
            assert result[0].type == "text"
            assert "error" in result[0].text.lower()

    @pytest.mark.parametrize(
        "host,expected_success",
        [
            ("google.com", True),
            ("8.8.8.8", True),
            ("192.168.1.1", True),
            ("", False),
            (None, False),
        ],
    )
    def test_service_discovery_valid_inputs(self, host, expected_success):
        """Test service_discovery with valid inputs."""
        with patch.object(self.discovery_tools, "_execute_command") as mock_execute:
            mock_execute.return_value = {
                "success": expected_success,
                "stdout": "Service discovery results",
                "stderr": "",
                "return_code": 0 if expected_success else 1,
            }

            result = self.discovery_tools.service_discovery(host)

            assert len(result) > 0
            assert result[0].type == "text"

            if expected_success:
                assert "Service discovery" in result[0].text
            else:
                assert "error" in result[0].text.lower()

    @pytest.mark.parametrize(
        "host",
        [
            "",
            None,
            "invalid..host",
        ],
    )
    def test_service_discovery_invalid_host(self, host):
        """Test service_discovery with invalid hosts."""
        result = self.discovery_tools.service_discovery(host)

        assert len(result) > 0
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_service_discovery_command_timeout(self):
        """Test service_discovery with command timeout."""
        with patch.object(self.discovery_tools, "_execute_command") as mock_execute:
            mock_execute.side_effect = TimeoutError("Command timed out")

            result = self.discovery_tools.service_discovery("google.com")

            assert len(result) > 0
            assert result[0].type == "text"
            assert "error" in result[0].text.lower()

    @pytest.mark.parametrize(
        "valid_hosts,invalid_hosts",
        [
            (
                ["google.com", "8.8.8.8", "192.168.1.1"],
                ["", None, "invalid..host", "host with spaces"],
            ),
        ],
    )
    def test_validate_host(self, valid_hosts, invalid_hosts):
        """Test host validation."""
        for host in valid_hosts:
            assert self.discovery_tools._validate_host(host) is True

        for host in invalid_hosts:
            assert self.discovery_tools._validate_host(host) is False

    @pytest.mark.parametrize(
        "valid_scan_types,invalid_scan_types",
        [
            (["basic", "quick", "full"], ["", None, "invalid_type", "custom_scan"]),
        ],
    )
    def test_validate_scan_type(self, valid_scan_types, invalid_scan_types):
        """Test scan type validation."""
        for scan_type in valid_scan_types:
            assert self.discovery_tools._validate_scan_type(scan_type) is True

        for scan_type in invalid_scan_types:
            assert self.discovery_tools._validate_scan_type(scan_type) is False
