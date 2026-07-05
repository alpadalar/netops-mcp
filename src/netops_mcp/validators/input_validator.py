"""
Input validation for NetOps MCP server.

Provides comprehensive input validation and sanitization to prevent:
- Command injection attacks
- Path traversal attacks
- Invalid network parameters
- Malformed URLs and domains
"""

import re
import ipaddress
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

# Cloud instance-metadata endpoints (IPv4 link-local IMDS + the IPv6 variant).
_METADATA = {
    ipaddress.ip_address("169.254.169.254"),
    ipaddress.ip_address("fd00:ec2::254"),
}


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
    if re.search(r'[;&|`$\(\)\{\}<>\n\r]', hostname):
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
    hostname_pattern = r'^(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*$'
    
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
        raise ValidationError(f"Invalid IP address: {e}")
    
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
        allowed_schemes = ['http', 'https']
    
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValidationError(f"Invalid URL format: {e}")
    
    if not parsed.scheme:
        raise ValidationError("URL must have a scheme (http:// or https://)")
    
    if parsed.scheme not in allowed_schemes:
        raise ValidationError(f"URL scheme must be one of {allowed_schemes}, got {parsed.scheme}")
    
    if not parsed.netloc:
        raise ValidationError("URL must have a network location (domain/IP)")
    
    # Check for dangerous characters
    if re.search(r'[;&|`$\(\)\{\}<>\n\r]', url):
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
    if re.search(r'[;&|`$\(\)\{\}<>\n\r\s]', domain):
        raise ValidationError("Domain contains invalid characters")
    
    # Domain pattern: labels separated by dots
    # Each label: 1-63 chars, alphanumeric and hyphens, cannot start/end with hyphen
    domain_pattern = r'^(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*\.[a-zA-Z]{2,}$'
    
    # Allow single-label domains (for internal networks)
    single_label_pattern = r'^(?!-)[a-zA-Z0-9-]{1,63}(?<!-)$'
    
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
    if '\x00' in arg:
        raise ValidationError("Argument contains null bytes")
    
    # Check for command injection patterns
    dangerous_patterns = [
        r';\s*\w+',  # Command chaining with semicolon
        r'\|\s*\w+',  # Pipe to another command
        r'&&\s*\w+',  # AND command chaining
        r'\|\|\s*\w+',  # OR command chaining
        r'`[^`]*`',  # Backtick command substitution
        r'\$\([^\)]*\)',  # Command substitution
        r'>\s*[/\w]',  # Output redirection
        r'<\s*[/\w]',  # Input redirection
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
    if re.search(r'[^0-9,\-]', port_range):
        raise ValidationError("Port range contains invalid characters")
    
    # Validate individual ports and ranges
    parts = port_range.split(',')
    for part in parts:
        part = part.strip()
        if '-' in part:
            # Range
            try:
                start, end = part.split('-')
                start_port = int(start)
                end_port = int(end)
                validate_port(start_port)
                validate_port(end_port)
                if start_port > end_port:
                    raise ValidationError(f"Invalid port range: {part} (start > end)")
            except ValueError:
                raise ValidationError(f"Invalid port range format: {part}")
        else:
            # Single port
            try:
                validate_port(int(part))
            except ValueError:
                raise ValidationError(f"Invalid port number: {part}")
    
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


