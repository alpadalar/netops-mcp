"""
Network discovery tools for NetOps MCP.
"""

import re
from typing import Dict, List, Optional
from mcp.types import TextContent as Content
from ..base import NetOpsTool


class DiscoveryTools(NetOpsTool):
    """Tools for network discovery and scanning."""

    def _validate_scan_type(self, scan_type: str) -> bool:
        """Validate scan type.

        Args:
            scan_type: Scan type to validate

        Returns:
            True if scan type is valid
        """
        if not scan_type or not isinstance(scan_type, str):
            return False
        
        valid_scan_types = ['basic', 'quick', 'full']
        return scan_type.lower() in valid_scan_types

    def nmap_scan(self, target: str, ports: Optional[str] = None, scan_type: str = "basic", timeout: int = 300) -> List[Content]:
        """Scan network using nmap.

        Args:
            target: Target host or network
            ports: Port range (e.g., '22,80,443' or '1-1000')
            scan_type: Scan type (basic, quick, full)
            timeout: Timeout in seconds

        Returns:
            List of Content objects with nmap results
        """
        try:
            if not self._validate_host(target):
                raise ValueError("Invalid target provided")

            # SEC-03: SSRF-classify the scan target (loopback/link-local blocked
            # by default; private/global allowed). NON-HTTP fail-OPEN: an
            # unresolvable host proceeds to report the natural nmap failure.
            self._enforce_ssrf(target)

            if not self._validate_scan_type(scan_type):
                raise ValueError("Invalid scan type provided")

            # SEC-05 (two-layer ruling): quick (-sS) and full (-sS -sV -O) use
            # privileged nmap flags that require raw sockets. Gate them on the
            # app-layer config flag (default False). basic (-sT) and the -sV
            # connect scans are NEVER gated. ping/arping raw sockets ride the
            # separate Docker NET_RAW capability layer, not this flag.
            PRIVILEGED = {"quick", "full"}
            if scan_type in PRIVILEGED and not self._security.allow_privileged_commands:
                raise ValueError(
                    f"Scan type '{scan_type}' uses privileged nmap flags (-sS/-O) which are "
                    "disabled by config (security.allow_privileged_commands=false)."
                )

            # Build nmap command based on scan type
            if scan_type == "basic":
                command = ['nmap', '-sT', '-T4']
            elif scan_type == "quick":
                command = ['nmap', '-sS', '-T4', '--top-ports', '100']
            elif scan_type == "full":
                command = ['nmap', '-sS', '-sV', '-O', '-T4']
            else:
                command = ['nmap', '-sT', '-T4']
            
            # Add port specification
            if ports:
                command.extend(['-p', ports])
            
            # Add target
            command.append(target)
            
            result = self._execute_command(command, timeout)
            
            response_data = {
                "target": target,
                "ports": ports,
                "scan_type": scan_type,
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "return_code": result["return_code"]
            }
            
            return self._format_response(response_data, "nmap_scan")
            
        except Exception as e:
            return self._handle_error("nmap scan", e)

    def service_discovery(self, target: str, ports: Optional[str] = None) -> List[Content]:
        """Discover network services on a target.

        Args:
            target: Target host
            ports: Port range to scan

        Returns:
            List of Content objects with service discovery results
        """
        try:
            if not self._validate_host(target):
                raise ValueError("Invalid target provided")

            # SEC-03: SSRF-classify the target. service_discovery uses -sV -sC
            # (connect scan) so it is NOT privileged-gated per the two-layer ruling.
            self._enforce_ssrf(target)

            # Use nmap for service discovery
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
            
            return self._format_response(response_data, "service_discovery")
            
        except Exception as e:
            return self._handle_error("service discovery", e)
