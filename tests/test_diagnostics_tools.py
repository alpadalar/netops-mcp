"""Tests for the v1.2 diagnostics tools (TLS, WHOIS, reverse DNS, email DNS)."""

import json
import socket
import ssl
from unittest.mock import MagicMock, patch

import pytest

from netops_mcp.tools.network.diagnostics_tools import DiagnosticsTools


@pytest.fixture
def tools():
    return DiagnosticsTools()


def _load(result):
    return json.loads(result[0].text)


def test_tls_rejects_invalid_host(tools):
    assert _load(tools.tls_certificate_check("bad host; rm -rf /"))["error"] is True


def test_tls_blocks_metadata_address(tools):
    out = _load(tools.tls_certificate_check("169.254.169.254"))
    assert out["error"] is True


def test_tls_summarizes_certificate(tools):
    cert = {
        "subject": ((("commonName", "example.com"),),),
        "issuer": ((("organizationName", "Test CA"),),),
        "serialNumber": "01",
        "notBefore": "Jan  1 00:00:00 2020 GMT",
        "notAfter": "Jan  1 00:00:00 2099 GMT",
        "subjectAltName": (("DNS", "example.com"),),
    }
    tls = MagicMock()
    tls.getpeercert.return_value = cert
    tls.cipher.return_value = ("TLS_AES_256_GCM_SHA384", "TLSv1.3", 256)
    tls.version.return_value = "TLSv1.3"
    tls.__enter__ = lambda s: s
    tls.__exit__ = lambda *a: False
    ctx = MagicMock()
    ctx.wrap_socket.return_value = tls
    with (
        patch.object(tools, "_enforce_ssrf", return_value=["93.184.216.34"]),
        patch("ssl.create_default_context", return_value=ctx),
        patch("socket.create_connection") as cc,
    ):
        cc.return_value.__enter__ = lambda s: s
        cc.return_value.__exit__ = lambda *a: False
        out = _load(tools.tls_certificate_check("example.com"))
    assert out["verified"] is True
    assert out["subject"]["commonName"] == "example.com"
    assert out["san"] == ["example.com"]
    assert out["expired"] is False and out["days_remaining"] > 1000


def test_tls_reports_verification_failure(tools):
    ctx = MagicMock()
    err = ssl.SSLCertVerificationError(1, "bad")
    err.verify_message = "certificate has expired"
    ctx.wrap_socket.side_effect = err
    with (
        patch.object(tools, "_enforce_ssrf", return_value=["93.184.216.34"]),
        patch("ssl.create_default_context", return_value=ctx),
        patch("socket.create_connection") as cc,
    ):
        cc.return_value.__enter__ = lambda s: s
        cc.return_value.__exit__ = lambda *a: False
        out = _load(tools.tls_certificate_check("example.com"))
    assert out["verified"] is False
    assert "expired" in out["verify_error"]


def test_tls_timeout_is_structured_error(tools):
    with (
        patch.object(tools, "_enforce_ssrf", return_value=["93.184.216.34"]),
        patch("socket.create_connection", side_effect=socket.timeout()),
    ):
        assert _load(tools.tls_certificate_check("example.com"))["error"] is True


def test_whois_rejects_option_injection(tools):
    assert _load(tools.whois_lookup("-h evil.example"))["error"] is True


def test_whois_returns_record(tools):
    with patch.object(
        tools, "_execute_command", return_value={"success": True, "stdout": "Domain: x"}
    ) as ex:
        out = _load(tools.whois_lookup("example.com"))
    assert out["record"] == "Domain: x" and out["truncated"] is False
    assert ex.call_args[0][0] == ["whois", "example.com"]


def test_whois_failure(tools):
    with patch.object(tools, "_execute_command", return_value={"success": False, "stderr": "boom"}):
        assert _load(tools.whois_lookup("example.com"))["error"] is True


def test_reverse_dns_invalid_ip(tools):
    assert _load(tools.reverse_dns_lookup("not-an-ip"))["error"] is True


def test_reverse_dns_forward_confirmed(tools):
    import dns.resolver

    class R:
        def __init__(self, v):
            self.v = v

        def __str__(self):
            return self.v + "."

        def to_text(self):
            return self.v

    def fake_resolve(self, name, rtype="A", *a, **k):
        if rtype == "PTR":
            return [R("host.example.com")]
        if rtype == "A":
            return [R("192.0.2.10")]
        raise dns.resolver.NoAnswer()

    with patch.object(dns.resolver.Resolver, "resolve", fake_resolve):
        out = _load(tools.reverse_dns_lookup("192.0.2.10"))
    assert out["ptr"] == [{"name": "host.example.com", "forward_confirmed": True}]


def test_email_dns_check_findings(tools):
    import dns.resolver

    class R:
        def __init__(self, v):
            self.v = v

        def to_text(self):
            return self.v

    def fake_resolve(self, name, rtype="A", *a, **k):
        if rtype == "MX":
            return [R("10 mail.example.com.")]
        if rtype == "TXT" and name == "example.com":
            return [R('"v=spf1 +all"')]
        if rtype == "TXT" and name == "_dmarc.example.com":
            return [R('"v=DMARC1; p=none"')]
        raise dns.resolver.NoAnswer()

    with patch.object(dns.resolver.Resolver, "resolve", fake_resolve):
        out = _load(tools.email_dns_check("example.com", dkim_selector="s1"))
    joined = " ".join(out["findings"])
    assert "+all" in joined and "p=none" in joined and "DKIM" in joined
    assert out["mx"] == ["10 mail.example.com."]


def test_email_dns_check_invalid_domain(tools):
    assert _load(tools.email_dns_check("bad domain!"))["error"] is True


def test_tls_connects_to_pinned_ip_not_hostname(tools):
    """Rebind regression: connect to the classified IP, keep SNI/verification on host."""
    ctx = MagicMock()
    tls = MagicMock()
    tls.getpeercert.return_value = {}
    tls.cipher.return_value = None
    tls.__enter__ = lambda s: s
    tls.__exit__ = lambda *a: False
    ctx.wrap_socket.return_value = tls
    with (
        patch.object(tools, "_enforce_ssrf", return_value=["93.184.216.34"]),
        patch("ssl.create_default_context", return_value=ctx),
        patch("socket.create_connection") as cc,
    ):
        cc.return_value.__enter__ = lambda s: s
        cc.return_value.__exit__ = lambda *a: False
        tools.tls_certificate_check("rebind.example.com")
    assert cc.call_args[0][0] == ("93.184.216.34", 443)
    assert ctx.wrap_socket.call_args.kwargs["server_hostname"] == "rebind.example.com"


def test_tls_fails_closed_when_unresolvable(tools):
    with (
        patch.object(tools, "_enforce_ssrf", return_value=[]),
        patch("socket.create_connection") as cc,
    ):
        out = _load(tools.tls_certificate_check("nx.invalid"))
    assert out["error"] is True
    cc.assert_not_called()
