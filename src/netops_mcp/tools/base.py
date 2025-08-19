"""
Base classes and utilities for DevOps MCP tools.

This module provides the foundation for all DevOps MCP tools, including:
- Base tool class with common functionality
- Response formatting utilities
- Error handling mechanisms
- Logging setup
"""

import logging
import subprocess
from typing import Any, Dict, List, Optional, Union
from mcp.types import TextContent as Content


class DevOpsTool:
    """Base class for DevOps MCP tools.
    
    This class provides common functionality used by all DevOps tool implementations:
    - Standardized logging
    - Response formatting
    - Error handling
    - Subprocess execution
    """

    def __init__(self):
        """Initialize the tool."""
        self.logger = logging.getLogger(f"devops-mcp.{self.__class__.__name__.lower()}")

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
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout
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
        
        # Basic validation - could be enhanced with regex
        return len(host.strip()) > 0

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
