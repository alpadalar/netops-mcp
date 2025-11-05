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
from typing import Optional
from urllib.parse import urlparse


class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass


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
    hostname_pattern = r'^(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(\\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*$'
    
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
    domain_pattern = r'^(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(\\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*\\.[a-zA-Z]{2,}$'
    
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


