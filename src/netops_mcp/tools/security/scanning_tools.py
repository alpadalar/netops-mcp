"""
Security scanning tools for DevOps MCP.
"""

from typing import Dict, List, Optional
from mcp.types import TextContent as Content
from ..base import DevOpsTool


class ScanningTools(DevOpsTool):
    """Tools for security scanning and enumeration."""

    def port_scan(self, target: str, ports: str, timeout: int = 60) -> List[Content]:
        """Scan ports on a target.

        Args:
            target: Target host
            ports: Port range (e.g., '1-1000' or '22,80,443')
            timeout: Timeout in seconds

        Returns:
            List of Content objects with port scan results
        """
        try:
            if not self._validate_host(target):
                raise ValueError("Invalid target provided")

            # Use nmap for port scanning
            command = ['nmap', '-sT', '-T4', '-p', ports, target]
            result = self._execute_command(command, timeout)
            
            response_data = {
                "target": target,
                "ports": ports,
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "return_code": result["return_code"]
            }
            
            return self._format_response(response_data, "port_scan")
            
        except Exception as e:
            return self._handle_error("port scan", e)

    def service_enumeration(self, target: str, ports: Optional[str] = None) -> List[Content]:
        """Enumerate services on a target.

        Args:
            target: Target host
            ports: Optional port range

        Returns:
            List of Content objects with service enumeration results
        """
        try:
            if not self._validate_host(target):
                raise ValueError("Invalid target provided")

            # Use nmap for service enumeration
            command = ['nmap', '-sV', '-sC', '--version-intensity', '5']
            
            if ports:
                command.extend(['-p', ports])
            
            command.append(target)
            
            result = self._execute_command(command, 180)
            
            response_data = {
                "target": target,
                "ports": ports,
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "return_code": result["return_code"]
            }
            
            return self._format_response(response_data, "service_enumeration")
            
        except Exception as e:
            return self._handle_error("service enumeration", e)
