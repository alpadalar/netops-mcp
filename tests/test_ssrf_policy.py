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

import pytest

from netops_mcp.config.models import SecurityConfig
from netops_mcp.validators import input_validator
from netops_mcp.validators.input_validator import ValidationError, enforce_ssrf


# Every entry collapses to loopback / link-local / cloud-metadata once resolved,
# so all must be BLOCKED under the secure default policy.
BLOCKED = [
    "127.0.0.1",               # loopback literal
    "2130706433",              # decimal encoding of 127.0.0.1
    "0x7f000001",              # hex encoding of 127.0.0.1
    "0177.0.0.1",             # octal first-octet encoding of 127.0.0.1
    "::1",                     # IPv6 loopback
    "169.254.169.254",         # link-local / cloud metadata endpoint
    "::ffff:169.254.169.254",  # IPv4-mapped link-local (must unwrap)
    "::ffff:127.0.0.1",        # IPv4-mapped loopback (must unwrap)
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
