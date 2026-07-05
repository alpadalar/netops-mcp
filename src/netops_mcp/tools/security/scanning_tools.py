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
            # SEC-03 / CR-01: range-aware validate + SSRF-classify the scan
            # target. nmap CIDR/octet-range/wildcard syntax is expanded and every
            # covered address classified (loopback/link-local/metadata blocked by
            # default), and an unresolvable host fails CLOSED — so octet-range
            # targets can no longer slip past via resolver fail-open. port_scan
            # uses -sT (connect scan) so it is NOT privileged-gated. WR-02: a
            # plain hostname returns pinned resolved IP(s) so nmap scans the
            # classified address, not a name it could re-resolve to a rebind
            # target; literal/range/CIDR targets return None.
            pinned = self._enforce_ssrf_scan_target(target)

            if not self._validate_ports(ports):
                raise ValueError("Invalid ports specification provided")

            # Use nmap for port scanning. Target is the pinned resolved IP(s) for
            # a plain hostname (WR-02), else the original literal/range/CIDR.
            command = ['nmap', '-sT', '-T4', '-p', ports]
            command.extend(pinned if pinned else [target])
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
            # SEC-03 / CR-01: range-aware validate + SSRF-classify the scan
            # target (fails CLOSED on unresolvable; expands nmap range/CIDR
            # syntax and classifies every covered address). service_enumeration
            # uses -sV -sC (connect scan) so it is NOT privileged-gated. WR-02: a
            # plain hostname returns pinned resolved IP(s) handed to nmap below.
            pinned = self._enforce_ssrf_scan_target(target)

            if ports and not self._validate_ports(ports):
                raise ValueError("Invalid ports specification provided")

            # Use nmap for service enumeration
            command = ['nmap', '-sV', '-sC', '--version-intensity', '5']

            if ports:
                command.extend(['-p', ports])

            # Add target: pinned resolved IP(s) for a plain hostname (WR-02),
            # else the original literal/range/CIDR target passed through.
            if pinned:
                command.extend(pinned)
            else:
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
