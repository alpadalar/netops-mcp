"""
Security scanning tools for NetOps MCP.
"""

from typing import Dict, List, Optional
from mcp.types import TextContent as Content
from ..base import NetOpsTool


class ScanningTools(NetOpsTool):
    """Tools for security scanning and enumeration."""

    def _validate_ports(self, ports: str) -> bool:
        """Validate port specification by delegating to the central
        validate_port_range (REF-02).

        Keeps the historical ``-> bool`` contract: True for a well-formed port
        spec ("22,80,443", "1-1000"), False otherwise. The ad-hoc regex is gone
        — port-spec format is now a single source of truth in
        ``validators/input_validator.py``.

        Args:
            ports: Port specification to validate

        Returns:
            True if ports specification is valid
        """
        from ...validators.input_validator import (
            ValidationError,
            validate_port_range,
        )

        try:
            validate_port_range(ports)
            return True
        except ValidationError:
            return False

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

            # SEC-03: SSRF-classify the scan target (loopback/link-local blocked
            # by default; private/global allowed). port_scan uses -sT (connect
            # scan) so it is NOT privileged-gated per the two-layer ruling.
            self._enforce_ssrf(target)

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

            # SEC-03: SSRF-classify the target. service_enumeration uses -sV -sC
            # (connect scan) so it is NOT privileged-gated per the two-layer ruling.
            self._enforce_ssrf(target)

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
