"""SSRF bypass-corpus + DNS-rebind + allow-LAN characterization for
``enforce_ssrf`` (SEC-03 / TEST-04).

Red-first: this module imports ``enforce_ssrf``, which does not exist until the
resolve-then-classify classifier lands (Task 3). Until then the whole module
fails at collection (ImportError) — the intended proof that the corpus
exercises real enforcement, not a stub.

The numeric/literal corpus resolves OFFLINE: glibc's ``inet_aton`` inside
``socket.getaddrinfo`` normalizes decimal/hex/octal encodings locally, so no
network and no mock are needed for the core corpus. IP literals classify
directly via ``ipaddress``. DNS-rebind patches the ``_resolve`` seam directly.
"""

import ipaddress
import socket

import pytest
from netops_mcp.config.models import SecurityConfig
from netops_mcp.validators import input_validator
from netops_mcp.validators.input_validator import (
    ValidationError,
    enforce_ssrf,
    enforce_ssrf_scan_target,
)

# Every entry collapses to loopback / link-local / cloud-metadata once resolved,
# so all must be BLOCKED under the secure default policy.
BLOCKED = [
    "127.0.0.1",  # loopback literal
    "2130706433",  # decimal encoding of 127.0.0.1
    "0x7f000001",  # hex encoding of 127.0.0.1
    "0177.0.0.1",  # octal first-octet encoding of 127.0.0.1
    "::1",  # IPv6 loopback
    "169.254.169.254",  # link-local / cloud metadata endpoint
    "::ffff:169.254.169.254",  # IPv4-mapped link-local (must unwrap)
    "::ffff:127.0.0.1",  # IPv4-mapped loopback (must unwrap)
]

# Private RFC1918 LAN and global targets are the legitimate diagnostic surface.
ALLOWED = [
    "192.168.1.1",
    "10.0.0.5",
    "172.16.5.4",
    "8.8.8.8",
]


@pytest.mark.parametrize("host", BLOCKED)
def test_ssrf_blocks_bypass_corpus(host):
    """Every loopback/link-local/metadata encoding is blocked under defaults."""
    with pytest.raises(ValidationError):
        enforce_ssrf(host, SecurityConfig())


@pytest.mark.parametrize("host", ALLOWED)
def test_ssrf_allows_private_and_global(host):
    """Private LAN and global targets resolve and are allowed (returns IPs)."""
    ips = enforce_ssrf(host, SecurityConfig())
    assert ips, "allowed host must return a non-empty resolved IP list"


def test_ssrf_dns_rebind_blocked(monkeypatch):
    """A benign name whose resolver returns a disallowed IP is blocked.

    DNS-rebind defense: classification happens on the RESOLVED IP, not the
    name, so a resolver that returns 169.254.169.254 for an innocuous host is
    rejected — the same resolved IPs are what HTTP tools later pin curl to.
    """
    monkeypatch.setattr(
        input_validator,
        "_resolve",
        lambda host, port: [ipaddress.ip_address("169.254.169.254")],
    )
    with pytest.raises(ValidationError):
        enforce_ssrf("benign-name.example", SecurityConfig())


@pytest.mark.parametrize("host", ["192.168.1.1", "10.0.0.5"])
def test_ssrf_does_not_overblock_lan(host):
    """allow_private=True (default) must NOT over-block RFC1918 LAN targets."""
    ips = enforce_ssrf(host, SecurityConfig())
    assert ips, "private LAN target must not be over-blocked"


def test_block_metadata_guards_ipv4_imds_independently():
    """WR-01: block_metadata must block the IPv4 IMDS endpoint even when
    allow_link_local=True. Before the fix, 169.254.169.254 classified as
    link_local and slipped past because the metadata rule was never reached."""
    policy = SecurityConfig(allow_link_local=True, block_metadata=True)
    with pytest.raises(ValidationError):
        enforce_ssrf("169.254.169.254", policy)


def test_block_metadata_guards_ipv4_mapped_imds():
    """The IPv4-mapped IMDS (::ffff:169.254.169.254) is also caught by the
    independent metadata guard when allow_link_local=True."""
    policy = SecurityConfig(allow_link_local=True, block_metadata=True)
    with pytest.raises(ValidationError):
        enforce_ssrf("::ffff:169.254.169.254", policy)


def test_metadata_allowed_when_link_local_allowed_and_not_blocked():
    """Opt-out path: allow_link_local=True + block_metadata=False lets the IMDS
    endpoint through (no independent metadata guard fires) — the flag semantics
    are honored in both directions."""
    policy = SecurityConfig(allow_link_local=True, block_metadata=False)
    ips = enforce_ssrf("169.254.169.254", policy)
    assert ips, "IMDS must be allowed when link-local is allowed and metadata not blocked"


# ---------------------------------------------------------------------------
# CR-01: range-aware SCAN-target enforcement (enforce_ssrf_scan_target).
# nmap octet-range / CIDR / wildcard syntax is expanded and every covered
# address classified, closing the resolver fail-open bypass. Scan tools also
# fail CLOSED on an unresolvable plain hostname.
# ---------------------------------------------------------------------------
SCAN_ALLOWED = [
    "192.168.1.0/24",  # private CIDR
    "10.0.0.1-50",  # private octet range
    "192.168.1.*",  # private wildcard octet
    "8.8.8.8",  # single global literal
    "8.8.8.0/24",  # global CIDR
]


@pytest.mark.parametrize(
    "target",
    [
        "127.0.0.1-10",
        "169.254.169.250-254",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "169.0.0.0/8",
        "127.0.0.1",
    ],
)
def test_scan_target_blocks_sensitive_ranges(target):
    """Every covered address of a loopback/link-local/metadata range is
    classified; the whole target is blocked under the default policy."""
    with pytest.raises(ValidationError):
        enforce_ssrf_scan_target(target, SecurityConfig())


@pytest.mark.parametrize("target", SCAN_ALLOWED)
def test_scan_target_allows_private_and_global_ranges(target):
    """Legitimate private/global range & CIDR targets are NOT over-blocked."""
    enforce_ssrf_scan_target(target, SecurityConfig())  # must not raise


def test_scan_target_fails_closed_on_unresolvable_hostname(monkeypatch):
    """A plain scan hostname that does not resolve fails CLOSED (raises),
    unlike the ping-family fail-OPEN posture."""

    def boom(host, port):
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr(input_validator, "_resolve", boom)
    with pytest.raises(ValidationError):
        enforce_ssrf_scan_target("scanme.example", SecurityConfig())


def test_scan_target_dns_rebind_blocked(monkeypatch):
    """A benign scan name whose resolver returns a disallowed IP is blocked —
    classification happens on the resolved IP, not the name."""
    monkeypatch.setattr(
        input_validator,
        "_resolve",
        lambda host, port: [ipaddress.ip_address("169.254.169.254")],
    )
    with pytest.raises(ValidationError):
        enforce_ssrf_scan_target("benign-name.example", SecurityConfig())


@pytest.mark.parametrize("target", ["", None, "invalid..host", "256.1.1.1"])
def test_scan_target_rejects_malformed(target):
    """Empty / malformed / out-of-range scan targets raise ValidationError."""
    with pytest.raises(ValidationError):
        enforce_ssrf_scan_target(target, SecurityConfig())


# ---------------------------------------------------------------------------
# WR-01: the >4096-address octet-range bounding-box FALLBACK
# (input_validator.py:270-278) is the load-bearing defense for large nmap
# octet ranges — the exact class the CR-01 bypass exploited — but every prior
# test stayed under the 4096 cap and took the exact-enumerate path, leaving the
# fallback (compute first/last, summarize_address_range, per-summary overlap
# check) with ZERO coverage. These cases force ranges >4096 so a future
# refactor that inverts the overlap sense or mis-computes min/max octets fails
# loudly instead of silently re-opening the bypass.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "target",
    [
        "1-255.1-255.0.1",  # 65025 addrs; bounding box straddles 127.0.0.0/8
        "120,200.0-255.0-255.1",  # 131072 addrs; non-contiguous comma straddles loopback
    ],
)
def test_scan_target_large_octet_range_fallback_blocks(target):
    """A >4096-address octet range whose bounding box overlaps a blocked
    network (loopback/link-local/metadata) is blocked via the summarize-range
    overlap fallback, not the exact-enumerate path."""
    with pytest.raises(ValidationError):
        enforce_ssrf_scan_target(target, SecurityConfig())


def test_scan_target_large_octet_range_fallback_allows_global():
    """A >4096-address octet range that is entirely global must NOT be
    over-blocked by the fallback (guards against an inverted overlap sense)."""
    # 1-9.1-9.1-9.0-255 == 186624 addresses, bounding box [1.1.1.0, 9.9.9.255],
    # all global — no overlap with any blocked network.
    enforce_ssrf_scan_target("1-9.1-9.1-9.0-255", SecurityConfig())  # must not raise
