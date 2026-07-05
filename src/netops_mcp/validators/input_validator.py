"""
Input validation for NetOps MCP server.

Provides comprehensive input validation and sanitization to prevent:
- Command injection attacks
- Path traversal attacks
- Invalid network parameters
- Malformed URLs and domains
"""

import ipaddress
import itertools
import re
import socket
from typing import List, Optional, Union
from urllib.parse import urlparse

from ..config.models import SecurityConfig


class ValidationError(Exception):
    """Exception raised for validation errors."""

    pass


# Union of the two concrete ipaddress leaf types (mypy-friendly; avoids the
# private ipaddress._BaseAddress).
_IPAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
# Union of the two concrete ipaddress network types (range/CIDR scan guard).
_IPNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]

# Cloud instance-metadata endpoints (IPv4 link-local IMDS + the IPv6 variant).
_METADATA = {
    ipaddress.ip_address("169.254.169.254"),
    ipaddress.ip_address("fd00:ec2::254"),
}

# Sensitive network blocks mirroring the per-address _category() ladder. Used
# ONLY by the range/CIDR SCAN-target guard (enforce_ssrf_scan_target) to test a
# whole nmap range for overlap when it is too large to enumerate address by
# address. Kept beside _METADATA so the address- and network-level views of the
# same sensitive space stay in sync (SEC-03 / CR-01).
_LOOPBACK_NETS = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
)
_LINK_LOCAL_NETS = (
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("fe80::/10"),
)
_METADATA_NETS = (
    ipaddress.ip_network("169.254.169.254/32"),
    ipaddress.ip_network("fd00:ec2::254/128"),
)
_PRIVATE_NETS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("fc00::/7"),
)

# Range/CIDR scan targets at or below this many addresses are classified
# address-by-address (exact, reuses _category); larger ranges fall back to
# network-overlap against _blocked_networks (safe; may slightly over-block a
# huge non-contiguous range, which is acceptable for a scanner).
_SCAN_ENUM_CAP = 4096

# One nmap IPv4 octet spec: '*', a number, a hyphen range, or a comma list of
# either (e.g. '1-10', '1,3,5', '10-20,30').
_IPV4_OCTET_RE = re.compile(r"^(?:\*|\d{1,3}(?:-\d{1,3})?(?:,\d{1,3}(?:-\d{1,3})?)*)$")


def _resolve(host: str, port: int) -> List[_IPAddress]:
    """Resolve a host to concrete IP objects (resolve step of SSRF policy).

    SEAM: tests patch this (or ``socket.getaddrinfo``) to inject rebind or
    loopback answers. IP literals take a fast path; names AND alternate
    encodings (decimal ``2130706433``, hex ``0x7f000001``, octal ``0177.0.0.1``)
    go through ``getaddrinfo``, which normalizes all radixes to the real IP
    offline (glibc ``inet_aton``) — so no custom radix parser is needed.
    """
    try:
        return [ipaddress.ip_address(host)]  # fast path: real IP literal
    except ValueError:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        # info[4][0] is the sockaddr address string; str() narrows the
        # getaddrinfo sockaddr union (str | int) for mypy and is a no-op at
        # runtime. split("%") strips any IPv6 zone id.
        return [ipaddress.ip_address(str(info[4][0]).split("%")[0]) for info in infos]


def _effective(ip: _IPAddress) -> _IPAddress:
    """Unwrap an IPv4-mapped IPv6 address (``::ffff:127.0.0.1``) to its IPv4
    body so it classifies by the real IPv4 address, not as a global IPv6 host."""
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    return ip


def _is_metadata(ip: _IPAddress) -> bool:
    """True if ``ip`` (or its IPv4-mapped body) is a cloud metadata endpoint."""
    return ip in _METADATA or _effective(ip) in _METADATA


def _category(ip: _IPAddress) -> str:
    """Classify an IP into an SSRF-relevant category via a precedence ladder.

    Precedence is load-bearing: ``is_private`` is True for loopback AND
    link-local (they are subsets), so classifying by independent flags would let
    ``allow_private=True`` wrongly permit loopback. IPv4-mapped IPv6
    (``::ffff:127.0.0.1``) is unwrapped first so it classifies by its IPv4 body.
    """
    eff = _effective(ip)
    if eff.is_loopback:
        return "loopback"
    if eff.is_link_local:  # incl. 169.254.0.0/16 metadata range
        return "link_local"
    if ip in _METADATA or eff in _METADATA:
        return "metadata"
    if eff.is_private:  # RFC1918 remainder
        return "private"
    if eff.is_reserved or eff.is_multicast or eff.is_unspecified:
        return "reserved"
    return "global"


def _apply_policy(host: str, ip: _IPAddress, policy: SecurityConfig) -> None:
    """Enforce the SSRF category policy for one resolved/covered IP; raise on block.

    ``block_metadata`` is an INDEPENDENT guard evaluated FIRST: a cloud-metadata
    endpoint (IPv4 ``169.254.169.254`` or IPv6 ``fd00:ec2::254``) is blocked
    whenever ``block_metadata`` is set, regardless of whether it ALSO classifies
    as link-local. Previously the IPv4 IMDS classified as ``link_local`` before
    the metadata rule was reached, so ``block_metadata=True`` gave NO independent
    protection for the IPv4 IMDS once ``allow_link_local=True`` — the flag's
    promise is now honored regardless of the link-local decision (WR-01).
    """
    if policy.block_metadata and _is_metadata(ip):
        raise ValidationError(f"{host} -> {ip} is cloud metadata (blocked)")
    category = _category(ip)
    if category == "loopback" and not policy.allow_loopback:
        raise ValidationError(f"{host} -> {ip} is loopback (blocked)")
    if category == "link_local" and not policy.allow_link_local:
        raise ValidationError(f"{host} -> {ip} is link-local (blocked)")
    if category == "private" and not policy.allow_private:
        raise ValidationError(f"{host} -> {ip} is private (blocked)")
    if category == "reserved":
        raise ValidationError(f"{host} -> {ip} is reserved (blocked)")


def enforce_ssrf(host: str, policy: SecurityConfig, port: int = 80) -> List[_IPAddress]:
    """Resolve-then-classify a connection target; raise on a blocked category.

    Returns the resolved IPs (HTTP tools pin curl to these via ``--resolve`` to
    defeat DNS-rebind). Raises ``ValidationError`` when any resolved IP falls in
    a category disallowed by ``policy``. Every SSRF-bypass encoding collapses to
    one real IP the moment it is resolved, so the whole bypass corpus is
    defeated here rather than by an ever-growing string blocklist.
    """
    ips = _resolve(host, port)
    for ip in ips:
        _apply_policy(host, ip, policy)
    return ips


def _blocked_networks(policy: SecurityConfig) -> List[_IPNetwork]:
    """Networks disallowed under ``policy`` (loopback / link-local / metadata,
    plus RFC1918 private when ``allow_private`` is False). Used by the
    range-overlap fallback for scan ranges too large to enumerate."""
    blocked: List[_IPNetwork] = []
    if not policy.allow_loopback:
        blocked.extend(_LOOPBACK_NETS)
    if not policy.allow_link_local:
        blocked.extend(_LINK_LOCAL_NETS)
    if policy.block_metadata:
        blocked.extend(_METADATA_NETS)
    if not policy.allow_private:
        blocked.extend(_PRIVATE_NETS)
    return blocked


def _octet_values(spec: str) -> List[int]:
    """Expand one nmap IPv4 octet spec ('5', '1-10', '1,3,5', '*') to its ints."""
    if spec == "*":
        return list(range(256))
    values: List[int] = []
    for part in spec.split(","):
        if "-" in part:
            lo_s, hi_s = part.split("-", 1)
            lo, hi = int(lo_s), int(hi_s)
            if lo > hi:
                raise ValidationError(f"Invalid octet range '{part}' (start > end)")
            values.extend(range(lo, hi + 1))
        else:
            values.append(int(part))
    for value in values:
        if not 0 <= value <= 255:
            raise ValidationError(f"Octet value out of range (0-255): {value}")
    return values


def _looks_like_ipv4_range(target: str) -> bool:
    """True if ``target`` is dotted-quad nmap IPv4 syntax (single literal, or a
    per-octet range / wildcard / comma list) — i.e. all-numeric, never a DNS
    hostname that must go through the resolver."""
    parts = target.split(".")
    return len(parts) == 4 and all(_IPV4_OCTET_RE.match(part) for part in parts)


def _enforce_scan_network(host: str, net: _IPNetwork, policy: SecurityConfig) -> None:
    """Enforce policy across every address of a network. Small networks are
    classified address-by-address (exact, reuses ``_apply_policy``); large ones
    fall back to overlap against ``_blocked_networks``."""
    if net.num_addresses <= _SCAN_ENUM_CAP:
        for ip in net:
            _apply_policy(host, ip, policy)
        return
    for blocked in _blocked_networks(policy):
        if net.version == blocked.version and net.overlaps(blocked):
            raise ValidationError(f"{host} covers blocked network {blocked}")


def enforce_ssrf_scan_target(target: str, policy: SecurityConfig) -> Optional[List[str]]:
    """Validate + SSRF-enforce an nmap-family SCAN target (SEC-03 / CR-01).

    Scan targets differ from single connection targets (``enforce_ssrf``) in two
    security-relevant ways, both closed here:

      1. They may use nmap range / CIDR / wildcard syntax (``127.0.0.1-10``,
         ``169.254.0.0/16``, ``192.168.1.*``). Such a target is EXPANDED and
         EVERY covered address is classified; the scan is blocked if ANY covered
         address is loopback / link-local / cloud-metadata / (when configured)
         private / reserved. Plain ``validate_hostname`` accepts ``127.0.0.1-10``
         as a legal hostname and ``enforce_ssrf`` then fails OPEN when the range
         does not resolve — the exact bypass this closes.
      2. A plain hostname that does not resolve fails CLOSED (raises), unlike the
         diagnostic ping-family fail-OPEN posture: a scan target that will not
         resolve must not silently proceed to the nmap subprocess.

    Return contract (WR-02 DNS-rebind pin):
      * For a PLAIN HOSTNAME (or IPv6 literal), returns the deduped, ordered list
        of resolved+classified IP strings. Callers hand THESE to nmap instead of
        the name so nmap cannot independently re-resolve the hostname to a
        DNS-rebind target (127.0.0.1 / IMDS) after it passed classification.
      * For a range / CIDR / dotted-quad-literal target, returns None — nmap
        never re-resolves numeric syntax, so it is passed through unchanged.

    Raises ``ValidationError`` on a malformed target, a blocked category, or an
    unresolvable plain hostname.
    """
    if not target or not isinstance(target, str):
        raise ValidationError("Scan target must be a non-empty string")
    target = target.strip()

    # CIDR (127.0.0.0/8, 192.168.1.0/24, ...): classify the whole network.
    if "/" in target:
        try:
            net = ipaddress.ip_network(target, strict=False)
        except ValueError as exc:
            raise ValidationError(f"Invalid CIDR scan target: {target}") from exc
        _enforce_scan_network(target, net, policy)
        return None

    # Dotted-quad numeric syntax (single literal, per-octet range / wildcard /
    # comma list): expand and classify offline, no DNS.
    if _looks_like_ipv4_range(target):
        octet_sets = [_octet_values(part) for part in target.split(".")]
        total = 1
        for values in octet_sets:
            total *= len(values)
        if total <= _SCAN_ENUM_CAP:
            for combo in itertools.product(*octet_sets):
                addr = ".".join(str(part) for part in combo)
                _apply_policy(target, ipaddress.IPv4Address(addr), policy)
            return None
        first = ipaddress.IPv4Address(".".join(str(min(values)) for values in octet_sets))
        last = ipaddress.IPv4Address(".".join(str(max(values)) for values in octet_sets))
        for net in ipaddress.summarize_address_range(first, last):
            _enforce_scan_network(target, net, policy)
        return None

    # Plain hostname or IPv6 literal: format-check, then resolve-and-classify.
    # SCAN tools fail CLOSED on an unresolvable name (distinct from the
    # ping-family fail-OPEN A3 decision preserved for connectivity tools).
    try:
        validate_hostname(target)
    except ValidationError:
        validate_ip_address(target)
    try:
        ips = enforce_ssrf(target, policy)
    except socket.gaierror as exc:
        raise ValidationError(
            f"scan target '{target}' does not resolve; scan tools fail closed"
        ) from exc
    # WR-02: return the RESOLVED+classified IP(s) so the caller pins nmap to the
    # address it just classified rather than the name. nmap re-resolves a plain
    # hostname on its own, so a name that first resolves to a global IP (passing
    # classification) could rebind to 127.0.0.1 / 169.254.169.254 before nmap's
    # own lookup — the same DNS-rebind class as the httpie residual. An
    # IP-literal input round-trips unchanged (str(ip) == the literal). Deduped,
    # insertion-order preserved.
    return list(dict.fromkeys(str(ip) for ip in ips))


def validate_hostname(hostname: str, allow_localhost: bool = True) -> str:
    """
    Validate a hostname.

    Args:
        hostname: The hostname to validate
        allow_localhost: Whether to allow localhost/127.0.0.1

    Returns:
        Validated hostname

    Raises:
        ValidationError: If hostname is invalid
    """
    if not hostname or not isinstance(hostname, str):
        raise ValidationError("Hostname must be a non-empty string")

    # Remove whitespace
    hostname = hostname.strip()

    # Check length
    if len(hostname) > 253:
        raise ValidationError("Hostname too long (max 253 characters)")

    # Check for dangerous characters
    if re.search(r"[;&|`$\(\)\{\}<>\n\r]", hostname):
        raise ValidationError("Hostname contains invalid characters")

    # Try to parse as IP address first
    try:
        ip = ipaddress.ip_address(hostname)
        if not allow_localhost and ip.is_loopback:
            raise ValidationError("Localhost addresses not allowed")
        return hostname
    except ValueError:
        pass

    # Validate as hostname
    # Hostname labels can contain letters, digits, and hyphens
    # Cannot start or end with hyphen
    hostname_pattern = r"^(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*$"

    if not re.match(hostname_pattern, hostname):
        raise ValidationError(f"Invalid hostname format: {hostname}")

    return hostname


def validate_ip_address(ip: str, allow_private: bool = True, allow_localhost: bool = True) -> str:
    """
    Validate an IP address (IPv4 or IPv6).

    Args:
        ip: The IP address to validate
        allow_private: Whether to allow private IP addresses
        allow_localhost: Whether to allow localhost/127.0.0.1

    Returns:
        Validated IP address

    Raises:
        ValidationError: If IP address is invalid
    """
    if not ip or not isinstance(ip, str):
        raise ValidationError("IP address must be a non-empty string")

    ip = ip.strip()

    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError as e:
        raise ValidationError(f"Invalid IP address: {e}") from e

    if not allow_private and ip_obj.is_private:
        raise ValidationError("Private IP addresses not allowed")

    if not allow_localhost and ip_obj.is_loopback:
        raise ValidationError("Localhost addresses not allowed")

    return ip


def validate_port(port: int) -> int:
    """
    Validate a network port number.

    Args:
        port: The port number to validate

    Returns:
        Validated port number

    Raises:
        ValidationError: If port is invalid
    """
    if not isinstance(port, int):
        raise ValidationError("Port must be an integer")

    if port < 1 or port > 65535:
        raise ValidationError(f"Port must be between 1 and 65535, got {port}")

    return port


def validate_url(url: str, allowed_schemes: Optional[list] = None) -> str:
    """
    Validate a URL.

    Args:
        url: The URL to validate
        allowed_schemes: List of allowed schemes (default: http, https)

    Returns:
        Validated URL

    Raises:
        ValidationError: If URL is invalid
    """
    if not url or not isinstance(url, str):
        raise ValidationError("URL must be a non-empty string")

    url = url.strip()

    if allowed_schemes is None:
        allowed_schemes = ["http", "https"]

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValidationError(f"Invalid URL format: {e}") from e

    if not parsed.scheme:
        raise ValidationError("URL must have a scheme (http:// or https://)")

    if parsed.scheme not in allowed_schemes:
        raise ValidationError(f"URL scheme must be one of {allowed_schemes}, got {parsed.scheme}")

    if not parsed.netloc:
        raise ValidationError("URL must have a network location (domain/IP)")

    # Check for dangerous characters
    if re.search(r"[;&|`$\(\)\{\}<>\n\r]", url):
        raise ValidationError("URL contains invalid characters")

    return url


def validate_domain(domain: str) -> str:
    """
    Validate a domain name.

    Args:
        domain: The domain name to validate

    Returns:
        Validated domain name

    Raises:
        ValidationError: If domain is invalid
    """
    if not domain or not isinstance(domain, str):
        raise ValidationError("Domain must be a non-empty string")

    domain = domain.strip().lower()

    # Check length
    if len(domain) > 253:
        raise ValidationError("Domain too long (max 253 characters)")

    # Check for dangerous characters
    if re.search(r"[;&|`$\(\)\{\}<>\n\r\s]", domain):
        raise ValidationError("Domain contains invalid characters")

    # Domain pattern: labels separated by dots
    # Each label: 1-63 chars, alphanumeric and hyphens, cannot start/end with hyphen
    domain_pattern = (
        r"^(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*\.[a-zA-Z]{2,}$"
    )

    # Allow single-label domains (for internal networks)
    single_label_pattern = r"^(?!-)[a-zA-Z0-9-]{1,63}(?<!-)$"

    if not (re.match(domain_pattern, domain) or re.match(single_label_pattern, domain)):
        raise ValidationError(f"Invalid domain format: {domain}")

    return domain


def sanitize_command_arg(arg: str, max_length: int = 1000) -> str:
    """
    Sanitize a command argument to prevent injection attacks.

    Removes or escapes dangerous characters that could be used for
    command injection.

    Args:
        arg: The argument to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized argument

    Raises:
        ValidationError: If argument is too long or contains dangerous patterns
    """
    if not isinstance(arg, str):
        raise ValidationError("Argument must be a string")

    # Check length
    if len(arg) > max_length:
        raise ValidationError(f"Argument too long (max {max_length} characters)")

    # Check for null bytes
    if "\x00" in arg:
        raise ValidationError("Argument contains null bytes")

    # Check for command injection patterns
    dangerous_patterns = [
        r";\s*\w+",  # Command chaining with semicolon
        r"\|\s*\w+",  # Pipe to another command
        r"&&\s*\w+",  # AND command chaining
        r"\|\|\s*\w+",  # OR command chaining
        r"`[^`]*`",  # Backtick command substitution
        r"\$\([^\)]*\)",  # Command substitution
        r">\s*[/\w]",  # Output redirection
        r"<\s*[/\w]",  # Input redirection
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, arg):
            raise ValidationError(f"Argument contains potentially dangerous pattern: {pattern}")

    return arg


def validate_port_range(port_range: str) -> str:
    """
    Validate a port range string.

    Args:
        port_range: Port range (e.g., "80", "80-443", "80,443,8080")

    Returns:
        Validated port range

    Raises:
        ValidationError: If port range is invalid
    """
    if not port_range or not isinstance(port_range, str):
        raise ValidationError("Port range must be a non-empty string")

    port_range = port_range.strip()

    # Check for dangerous characters
    if re.search(r"[^0-9,\-]", port_range):
        raise ValidationError("Port range contains invalid characters")

    # Validate individual ports and ranges
    parts = port_range.split(",")
    for part in parts:
        part = part.strip()
        if "-" in part:
            # Range
            try:
                start, end = part.split("-")
                start_port = int(start)
                end_port = int(end)
                validate_port(start_port)
                validate_port(end_port)
                if start_port > end_port:
                    raise ValidationError(f"Invalid port range: {part} (start > end)")
            except ValueError:
                raise ValidationError(f"Invalid port range format: {part}") from None
        else:
            # Single port
            try:
                validate_port(int(part))
            except ValueError:
                raise ValidationError(f"Invalid port number: {part}") from None

    return port_range


def validate_timeout(timeout: int, min_timeout: int = 1, max_timeout: int = 600) -> int:
    """
    Validate a timeout value.

    Args:
        timeout: Timeout in seconds
        min_timeout: Minimum allowed timeout
        max_timeout: Maximum allowed timeout

    Returns:
        Validated timeout

    Raises:
        ValidationError: If timeout is invalid
    """
    if not isinstance(timeout, int):
        raise ValidationError("Timeout must be an integer")

    if timeout < min_timeout or timeout > max_timeout:
        raise ValidationError(
            f"Timeout must be between {min_timeout} and {max_timeout} seconds, got {timeout}"
        )

    return timeout
