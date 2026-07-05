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
        """Validate host parameter.

        Args:
            host: Host to validate

        Returns:
            True if host is valid
        """
        if not host or not isinstance(host, str):
            return False
        
        host = host.strip()
        if len(host) == 0:
            return False
        
        # Check for invalid patterns
        if '..' in host or ' ' in host:
            return False
        
        # Basic domain/IP validation
        import re
        # IP address pattern
        ip_pattern = re.compile(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
        # Domain pattern
        domain_pattern = re.compile(r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$')
        
        return bool(ip_pattern.match(host) or domain_pattern.match(host))

    def _validate_port(self, port: Union[int, str]) -> bool:
        """Validate port parameter.

        Args:
            port: Port to validate

        Returns:
            True if port is valid
        """
        try:
            port_num = int(port)
            return 1 <= port_num <= 65535
        except (ValueError, TypeError):
            return False
