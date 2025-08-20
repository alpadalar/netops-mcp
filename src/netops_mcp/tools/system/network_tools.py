"""
System network tools for NetOps MCP.
"""

from typing import Dict, List, Optional
from mcp.types import TextContent as Content
from ..base import NetOpsTool


class NetworkTools(NetOpsTool):
    """Tools for system network analysis."""

    def ss_connections(self, state: Optional[str] = None, protocol: Optional[str] = None) -> List[Content]:
        """Show network connections using ss.

        Args:
            state: Connection state filter
            protocol: Protocol filter (tcp/udp)

        Returns:
            List of Content objects with ss results
        """
        try:
            command = ['ss', '-tuln']
            
            if state:
                command.extend(['-o', f'state {state}'])
            
            if protocol:
                if protocol.lower() == 'tcp':
                    command = ['ss', '-tln']
                elif protocol.lower() == 'udp':
                    command = ['ss', '-uln']
            
            result = self._execute_command(command, 30)
            
            response_data = {
                "state": state,
                "protocol": protocol,
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "return_code": result["return_code"]
            }
            
            return self._format_response(response_data, "ss_connections")
            
        except Exception as e:
            return self._handle_error("ss connections", e)

    def netstat_connections(self, state: Optional[str] = None, protocol: Optional[str] = None) -> List[Content]:
        """Show network connections using netstat.

        Args:
            state: Connection state filter
            protocol: Protocol filter (tcp/udp)

        Returns:
            List of Content objects with netstat results
        """
        try:
            command = ['netstat', '-tuln']
            
            if state:
                command.extend(['--state', state])
            
            if protocol:
                if protocol.lower() == 'tcp':
                    command = ['netstat', '-tln']
                elif protocol.lower() == 'udp':
                    command = ['netstat', '-uln']
            
            result = self._execute_command(command, 30)
            
            response_data = {
                "state": state,
                "protocol": protocol,
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "return_code": result["return_code"]
            }
            
            return self._format_response(response_data, "netstat_connections")
            
        except Exception as e:
            return self._handle_error("netstat connections", e)

    def arp_table(self) -> List[Content]:
        """Show ARP table.

        Returns:
            List of Content objects with ARP table
        """
        try:
            command = ['arp', '-a']
            result = self._execute_command(command, 30)
            
            response_data = {
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "return_code": result["return_code"]
            }
            
            return self._format_response(response_data, "arp_table")
            
        except Exception as e:
            return self._handle_error("arp table", e)

    def arping_host(self, host: str, count: int = 4) -> List[Content]:
        """ARP ping a host.

        Args:
            host: Target host
            count: Number of packets

        Returns:
            List of Content objects with arping results
        """
        try:
            if not self._validate_host(host):
                raise ValueError("Invalid host provided")

            command = ['arping', '-c', str(count), host]
            result = self._execute_command(command, 30)
            
            response_data = {
                "host": host,
                "count": count,
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "return_code": result["return_code"]
            }
            
            return self._format_response(response_data, "arping_host")
            
        except Exception as e:
            return self._handle_error("arping host", e)
