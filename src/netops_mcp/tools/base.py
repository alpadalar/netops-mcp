"""
Base classes and utilities for NetOps MCP tools.

This module provides the foundation for all NetOps MCP tools, including:
- Base tool class with common functionality
- Response formatting utilities
- Error handling mechanisms
- Logging setup
"""

import logging
import subprocess
from typing import Any, Dict, List, Optional, Union
from mcp.types import TextContent as Content

from ..config.models import Config, SecurityConfig


class NetOpsTool:
    """Base class for NetOps MCP tools.
    
    This class provides common functionality used by all NetOps tool implementations:
    - Standardized logging
    - Response formatting
    - Error handling
    - Subprocess execution
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        """Initialize the tool.

        Args:
            config: Optional server configuration. When ``None`` (the direct
                construction path used by tool tests) the tool inherits a
                secure-by-default ``SecurityConfig``: loopback and link-local
                (incl. cloud metadata) are blocked, private/LAN is allowed, and
                privileged commands are off.
        """
        self.logger = logging.getLogger(f"netops-mcp.{self.__class__.__name__.lower()}")
        self._security: SecurityConfig = config.security if config else SecurityConfig()

    def _format_response(self, data: Any, tool_name: Optional[str] = None) -> List[Content]:
        """Format response data into MCP content.

        Args:
            data: Raw data to format
            tool_name: Name of the tool for context

        Returns:
            List of Content objects
        """
        import json
        
        if isinstance(data, dict):
            formatted = json.dumps(data, indent=2, default=str)
        elif isinstance(data, list):
            formatted = json.dumps(data, indent=2, default=str)
        else:
            formatted = str(data)

        return [Content(type="text", text=formatted)]

    def _execute_command(self, command: List[str], timeout: int = 30) -> Dict[str, Any]:
        """Execute a system command safely.

        Args:
            command: Command to execute as list
            timeout: Command timeout in seconds

        Returns:
            Dictionary containing command results
        """
        try:
            self.logger.debug(f"Executing command: {' '.join(command)}")
            
            # stdin=DEVNULL: capture_output only redirects stdout/stderr, so
            # without this every child spawned through this helper would
            # inherit the server's fd 0 — which in stdio transport mode IS
            # the MCP JSON-RPC stream. Interactive children (e.g. telnet)
            # would consume protocol bytes and forward them to an arbitrary
            # remote host (CR-01). Spawn sites outside this helper detach
            # stdin at their own call sites: utils/system_check.py routes
            # everything through its _run() wrapper and the
            # RUN_TESTS_ON_START pytest child in server.py passes
            # stdin=DEVNULL directly (WR-01).
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "command": ' '.join(command)
            }
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {' '.join(command)}")
            return {
                "success": False,
                "stdout": "",
                "stderr": "Command timed out",
                "return_code": -1,
                "command": ' '.join(command)
            }
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {' '.join(command)} - {e}")
            return {
                "success": False,
                "stdout": e.stdout or "",
                "stderr": e.stderr or str(e),
                "return_code": e.returncode,
                "command": ' '.join(command)
            }
        except FileNotFoundError:
            self.logger.error(f"Command not found: {command[0]}")
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command not found: {command[0]}",
                "return_code": -1,
                "command": ' '.join(command)
            }
        except Exception as e:
            self.logger.error(f"Unexpected error executing command: {e}")
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "command": ' '.join(command)
            }

    def _handle_error(self, operation: str, error: Exception) -> List[Content]:
        """Handle and log errors from operations.

        Args:
            operation: Description of the operation that failed
            error: The exception that occurred

        Returns:
            List of Content objects with error information
        """
        error_msg = str(error)
        self.logger.error(f"Failed to {operation}: {error_msg}")

        error_response = {
            "error": True,
            "operation": operation,
            "message": error_msg,
            "type": type(error).__name__
        }

        return self._format_response(error_response)

    def _validate_host(self, host: str) -> bool:
        """Validate host FORMAT by delegating to the central validators (REF-02).

        Keeps the historical ``-> bool`` contract: True for a well-formed
        hostname or IP literal, False otherwise. This is format-only — SSRF
        policy (loopback/link-local/metadata) is enforced separately by
        ``_enforce_ssrf`` / ``_enforce_ssrf_url``.

        Args:
            host: Host to validate

        Returns:
            True if host is a valid hostname or IP literal
        """
        from ..validators.input_validator import (
            ValidationError,
            validate_hostname,
            validate_ip_address,
        )

        try:
            validate_hostname(host)
            return True
        except ValidationError:
            pass
        try:
            validate_ip_address(host)
            return True
        except ValidationError:
            return False

    def _validate_port(self, port: Union[int, str]) -> bool:
        """Validate a port by delegating to the central validator (REF-02).

        Args:
            port: Port to validate

        Returns:
            True if port is a valid 1-65535 integer (or int-parseable string)
        """
        from ..validators.input_validator import ValidationError, validate_port

        try:
            return bool(validate_port(int(port)))
        except (ValueError, TypeError, ValidationError):
            return False

    def _enforce_ssrf(self, host: str, port: int = 0) -> list:
        """SSRF-classify a NON-HTTP connection target (ping/traceroute/nmap/...).

        Fail-OPEN on resolution failure (A3): a down or unresolvable host is a
        legitimate diagnostic target, so a ``socket.gaierror`` yields ``[]`` and
        the caller proceeds to report the natural failure. A resolved-but-blocked
        category (loopback/link-local/metadata) raises ``ValidationError``, which
        the tool's existing ``except Exception`` envelope converts to an error
        response — no new plumbing required.

        Args:
            host: The connection target (name or IP literal)
            port: Optional target port (used for resolution; 0 -> default 80)

        Returns:
            The resolved IP list (empty on unresolvable host)
        """
        import socket as _socket

        from ..validators.input_validator import enforce_ssrf

        try:
            return enforce_ssrf(host, self._security, port or 80)
        except _socket.gaierror:
            return []

    def _enforce_ssrf_scan_target(self, target: str) -> None:
        """Validate + SSRF-classify an nmap-family SCAN target (SEC-03 / CR-01).

        Unlike ``_enforce_ssrf`` (single connection target, fail-OPEN on an
        unresolvable diagnostic host), this is RANGE-AWARE: nmap
        CIDR/octet-range/wildcard syntax (``127.0.0.1-10``, ``169.254.0.0/16``,
        ``192.168.1.*``) is expanded and EVERY covered address is classified, and
        it fails CLOSED on an unresolvable plain hostname. A target that resolves
        to — or covers — loopback/link-local/cloud-metadata is blocked before the
        nmap subprocess runs, closing the octet-range fail-open bypass.
        ``ValidationError`` propagates to the tool's existing ``except Exception``
        envelope, which converts it to a structured error response.

        Args:
            target: The scan target (host, IP literal, or nmap range/CIDR)

        Raises:
            ValidationError: on a malformed target, a blocked category, or an
                unresolvable plain hostname
        """
        from ..validators.input_validator import enforce_ssrf_scan_target

        enforce_ssrf_scan_target(target, self._security)

    def _enforce_ssrf_url(self, url: str) -> list:
        """SSRF-classify an HTTP URL target and return the pinned IP list.

        Fail-CLOSED on resolution failure (A3): curl must never run unpinned, so
        an unresolvable host raises ``ValidationError`` rather than proceeding.
        The returned IPs are what HTTP tools pin curl to via ``--resolve``.

        Args:
            url: The request URL

        Returns:
            The resolved IP list for the URL host

        Raises:
            ValidationError: on a blocked category or an unresolvable host
        """
        import socket as _socket
        from urllib.parse import urlsplit

        from ..validators.input_validator import ValidationError, enforce_ssrf

        parts = urlsplit(url)
        host = parts.hostname
        if not host:
            raise ValidationError(f"URL has no host to resolve: {url}")
        port = parts.port or (443 if parts.scheme == "https" else 80)
        try:
            return enforce_ssrf(host, self._security, port)
        except _socket.gaierror as exc:
            raise ValidationError(f"could not resolve {host}") from exc
