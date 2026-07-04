"""
Characterization tests for formatting/OutputParser.

These tests lock the CURRENT parser behavior (plan 01-02) as the delegation
baseline for plan 01-04. Success and partial-loss paths are characterization
tests; the zero-transmitted stats-line case asserts the NEW locked behavior
introduced by plan 01-04 (BUG-01: loss 100, rtt fields None).
"""

import pytest
from netops_mcp.formatting.output_parser import OutputParser


class TestParsePingOutput:
    """Characterization tests for OutputParser.parse_ping_output."""

    def test_parse_ping_output_success(self, sample_ping_output):
        """Success output: exact stats values including float loss percent."""
        stats = OutputParser.parse_ping_output(sample_ping_output["stdout"])

        assert stats["packets_transmitted"] == 4
        assert stats["packets_received"] == 4
        assert isinstance(stats["packet_loss_percent"], float)
        assert stats["packet_loss_percent"] == 0.0
        assert stats["min_rtt"] == 1.23
        assert stats["avg_rtt"] == 1.395
        assert stats["max_rtt"] == 1.56
        assert stats["mdev_rtt"] == 0.134

    @pytest.mark.parametrize("stats_line,expected_loss", [
        ("4 packets transmitted, 4 received, 0% packet loss, time 3003ms", 0.0),
        ("4 packets transmitted, 2 received, 50% packet loss, time 3005ms", 50.0),
        ("4 packets transmitted, 3 received, 25% packet loss, time 3004ms", 25.0),
    ])
    def test_parse_ping_output_loss_percent(self, stats_line, expected_loss):
        """Loss percent is computed as float 100 - received/transmitted*100."""
        stats = OutputParser.parse_ping_output(stats_line)

        assert isinstance(stats["packet_loss_percent"], float)
        assert stats["packet_loss_percent"] == expected_loss

    def test_parse_ping_output_partial_loss(self, sample_ping_partial_loss_output):
        """Partial loss output: 50.0 percent loss with rtt fields parsed."""
        stats = OutputParser.parse_ping_output(sample_ping_partial_loss_output["stdout"])

        assert stats["packets_transmitted"] == 4
        assert stats["packets_received"] == 2
        assert stats["packet_loss_percent"] == 50.0
        assert stats["min_rtt"] == 1.23
        assert stats["avg_rtt"] == 1.34
        assert stats["max_rtt"] == 1.45
        assert stats["mdev_rtt"] == 0.11

    def test_parse_ping_output_unreachable_rtt_null(self, sample_ping_unreachable_output):
        """100% loss with packets transmitted (WR-02): rtt fields are None, not 0."""
        stats = OutputParser.parse_ping_output(sample_ping_unreachable_output["stdout"])

        assert stats["packets_transmitted"] == 2
        assert stats["packets_received"] == 0
        assert stats["packet_loss_percent"] == 100.0
        assert stats["min_rtt"] is None
        assert stats["avg_rtt"] is None
        assert stats["max_rtt"] is None
        assert stats["mdev_rtt"] is None

    def test_parse_ping_output_zero_transmitted(self, sample_ping_zero_tx_output):
        """Zero-tx stats block (BUG-01): loss 100, all rtt fields None."""
        stats = OutputParser.parse_ping_output(sample_ping_zero_tx_output["stdout"])

        assert stats["packets_transmitted"] == 0
        assert stats["packets_received"] == 0
        assert stats["packet_loss_percent"] == 100
        assert stats["min_rtt"] is None
        assert stats["avg_rtt"] is None
        assert stats["max_rtt"] is None
        assert stats["mdev_rtt"] is None

    def test_parse_ping_output_bsd_format(self):
        """macOS/BSD ping output (WR-03): '<n> packets received' and 'round-trip'."""
        bsd_output = """PING google.com (142.250.185.78): 56 data bytes
64 bytes from 142.250.185.78: icmp_seq=0 ttl=115 time=12.345 ms
64 bytes from 142.250.185.78: icmp_seq=1 ttl=115 time=13.456 ms

--- google.com ping statistics ---
4 packets transmitted, 4 packets received, 0.0% packet loss
round-trip min/avg/max/stddev = 12.345/13.456/14.567/0.789 ms"""

        stats = OutputParser.parse_ping_output(bsd_output)

        assert stats["packets_transmitted"] == 4
        assert stats["packets_received"] == 4
        assert stats["packet_loss_percent"] == 0.0
        assert stats["min_rtt"] == 12.345
        assert stats["avg_rtt"] == 13.456
        assert stats["max_rtt"] == 14.567
        assert stats["mdev_rtt"] == 0.789

    def test_parse_ping_output_bsd_unreachable(self):
        """macOS/BSD 100%-loss output (WR-03 + WR-02): loss parsed, rtt null."""
        bsd_output = """PING 192.0.2.1 (192.0.2.1): 56 data bytes
Request timeout for icmp_seq 0

--- 192.0.2.1 ping statistics ---
2 packets transmitted, 0 packets received, 100.0% packet loss"""

        stats = OutputParser.parse_ping_output(bsd_output)

        assert stats["packets_transmitted"] == 2
        assert stats["packets_received"] == 0
        assert stats["packet_loss_percent"] == 100.0
        assert stats["min_rtt"] is None
        assert stats["avg_rtt"] is None
        assert stats["max_rtt"] is None
        assert stats["mdev_rtt"] is None

    def test_parse_ping_output_no_stats_line(self):
        """Empty input keeps the default zero-valued stats dict."""
        stats = OutputParser.parse_ping_output("")

        assert stats["packets_transmitted"] == 0
        assert stats["packets_received"] == 0
        assert stats["packet_loss_percent"] == 0
        assert stats["min_rtt"] == 0
        assert stats["avg_rtt"] == 0
        assert stats["max_rtt"] == 0
        assert stats["mdev_rtt"] == 0


class TestParseTracerouteOutput:
    """Characterization tests for OutputParser.parse_traceroute_output."""

    def test_parse_traceroute_output_sample(self, sample_traceroute_output):
        """Sample output yields 5 hops with current field names and values."""
        hops = OutputParser.parse_traceroute_output(sample_traceroute_output["stdout"])

        assert len(hops) == 5
        assert hops[0]["hop_number"] == 1
        assert hops[0]["host"] == "_gateway"
        # WR-02: ip comes from the parenthesized "(ip)" token, not the hostname
        assert hops[0]["ip"] == "192.168.1.1"
        assert hops[0]["times"] == [1.234, 0.987, 1.123]
        # Timeout hop (* * *) is kept with empty times; no "(ip)" token, so
        # host and ip stay identical
        assert hops[3]["hop_number"] == 4
        assert hops[3]["host"] == "*"
        assert hops[3]["ip"] == "*"
        assert hops[3]["times"] == []
        assert hops[4]["hop_number"] == 5
        assert hops[4]["host"] == "google.com"
        assert hops[4]["ip"] == "142.250.185.78"
        assert hops[4]["times"] == [15.678, 15.432, 15.567]

    def test_parse_traceroute_output_skips_continuation_lines(self):
        """Non-numeric first token (WR-05): line is skipped, parse still succeeds."""
        output = """traceroute to example.com (93.184.216.34), 30 hops max, 60 byte packets
 1  _gateway (192.168.1.1)  1.234 ms  0.987 ms  1.123 ms
    alt-responder.example.net (10.9.9.9)  2.345 ms  2.456 ms  2.567 ms
 2  10.0.0.1 (10.0.0.1)  5.678 ms  5.432 ms  5.567 ms"""

        hops = OutputParser.parse_traceroute_output(output)

        # The wrapped responder line must be skipped, not raise ValueError
        assert len(hops) == 2
        assert hops[0]["hop_number"] == 1
        assert hops[1]["hop_number"] == 2


class TestParseMtrOutput:
    """Characterization tests for OutputParser.parse_mtr_output.

    The 4 tests below are migrated from tests/test_connectivity_tools.py
    (test_parse_mtr_output_*) and re-targeted at OutputParser with
    identical assertions; plan 01-04 deletes the originals together with
    the inline parsers.
    """

    def test_parse_mtr_output_valid(self):
        """Test mtr output parsing with valid output."""
        mtr_output = """Start: 2025-08-19T15:06:45+0000
HOST: test-host                Loss%   Snt   Last   Avg  Best  Wrst StDev
  1.|-- _gateway                0.0%     3    1.2   1.1   0.9   1.3   0.2
  2.|-- 10.0.0.1                0.0%     3    5.4   5.3   5.1   5.6   0.3
  3.|-- google.com              0.0%     3   15.3  15.4  15.1  15.7   0.3"""

        parsed = OutputParser.parse_mtr_output(mtr_output)

        # WR-01: real mtr --report hop lines ("1.|-- ...") must be parsed.
        assert "target" in parsed
        assert len(parsed["hops"]) == 3
        assert parsed["hops"][0]["host"] == "_gateway"
        assert parsed["hops"][0]["hop"] == 1
        assert parsed["hops"][0]["loss_percent"] == 0.0
        assert parsed["hops"][0]["snt"] == 3
        assert parsed["hops"][0]["last"] == 1.2
        assert parsed["hops"][0]["avg"] == 1.1
        assert parsed["hops"][0]["best"] == 0.9
        assert parsed["hops"][0]["worst"] == 1.3
        assert parsed["hops"][2]["host"] == "google.com"
        assert parsed["hops"][2]["hop"] == 3

    def test_parse_mtr_output_with_malformed_lines(self):
        """Test mtr output parsing with malformed lines."""
        mtr_output = """Start: 2025-08-19T15:06:45+0000
HOST: test-host                Loss%   Snt   Last   Avg  Best  Wrst StDev
  1.|-- _gateway                0.0%     3    1.2   1.1   0.9   1.3   0.2
  malformed line here
  2.|-- 10.0.0.1                0.0%     3    5.4   5.3   5.1   5.6   0.3
  another malformed line
  3.|-- google.com              0.0%     3   15.3  15.4  15.1  15.7   0.3"""

        parsed = OutputParser.parse_mtr_output(mtr_output)

        # Malformed lines are skipped; valid hop lines are still parsed (WR-01).
        assert "target" in parsed
        assert len(parsed["hops"]) == 3
        assert [h["hop"] for h in parsed["hops"]] == [1, 2, 3]

    def test_parse_mtr_output_empty(self):
        """Test mtr output parsing with empty output."""
        parsed = OutputParser.parse_mtr_output("")

        assert parsed["target"] == ""
        assert len(parsed["hops"]) == 0

    def test_parse_mtr_output_only_headers(self):
        """Test mtr output parsing with only header lines."""
        mtr_output = """Start: 2025-08-19T15:06:45+0000
HOST: test-host                Loss%   Snt   Last   Avg  Best  Wrst StDev"""

        parsed = OutputParser.parse_mtr_output(mtr_output)

        assert parsed["target"] == ""
        assert len(parsed["hops"]) == 0
