"""
Security scanning tools for NetOps MCP.
"""

import re
from typing import Dict, List, Optional
from mcp.types import TextContent as Content
from ..base import NetOpsTool


class ScanningTools(NetOpsTool):
    """Tools for security scanning and enumeration."""

    def _validate_ports(self, ports: str) -> bool:
        """Validate port specification.

        Args:
            ports: Port specification to validate

        Returns:
            True if ports specification is valid
        """
        if not ports or not isinstance(ports, str):
            return False
        
        # Check for common port patterns
        port_pattern = re.compile(r'^(\d+(-\d+)?)(,\d+(-\d+)?)*$')
        if not port_pattern.match(ports):
            return False
        
        # Validate individual port numbers
        parts = ports.split(',')
        for part in parts:
            if '-' in part:
                start, end = part.split('-')
                try:
                    start_port = int(start)
                    end_port = int(end)
                    if start_port > end_port or start_port < 1 or end_port > 65535:
                        return False
                except ValueError:
                    return False
            else:
                try:
                    port = int(part)
                    if port < 1 or port > 65535:
                        return False
                except ValueError:
                    return False
        
        return True

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
            
            if not self._validate_ports(ports):
                raise ValueError("Invalid ports specification provided")

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
            
            if ports and not self._validate_ports(ports):
                raise ValueError("Invalid ports specification provided")

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
