"""
DNS tools for DevOps MCP.
"""

from typing import Dict, List, Optional
from mcp.types import TextContent as Content
from ..base import DevOpsTool


class DNSTools(DevOpsTool):
    """Tools for DNS operations and queries."""

    def nslookup_query(self, domain: str, record_type: str = "A", server: Optional[str] = None) -> List[Content]:
        """Perform DNS lookup using nslookup.

        Args:
            domain: Domain to lookup
            record_type: DNS record type (A, AAAA, MX, TXT, etc.)
            server: Optional DNS server to use

        Returns:
            List of Content objects with nslookup results
        """
        try:
            if not self._validate_host(domain):
                raise ValueError("Invalid domain provided")

            command = ['nslookup', '-type=' + record_type, domain]
            if server:
                command.append(server)
            
            result = self._execute_command(command, 30)
            
            response_data = {
                "domain": domain,
                "record_type": record_type,
                "server": server,
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "return_code": result["return_code"]
            }
            
            return self._format_response(response_data, "nslookup_query")
            
        except Exception as e:
            return self._handle_error("nslookup query", e)

    def dig_query(self, domain: str, record_type: str = "A", server: Optional[str] = None) -> List[Content]:
        """Perform DNS lookup using dig.

        Args:
            domain: Domain to lookup
            record_type: DNS record type (A, AAAA, MX, TXT, etc.)
            server: Optional DNS server to use

        Returns:
            List of Content objects with dig results
        """
        try:
            if not self._validate_host(domain):
                raise ValueError("Invalid domain provided")

            command = ['dig', '+short', record_type, domain]
            if server:
                command.extend(['@' + server])
            
            result = self._execute_command(command, 30)
            
            response_data = {
                "domain": domain,
                "record_type": record_type,
                "server": server,
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "return_code": result["return_code"]
            }
            
            return self._format_response(response_data, "dig_query")
            
        except Exception as e:
            return self._handle_error("dig query", e)

    def host_lookup(self, domain: str, record_type: str = "A") -> List[Content]:
        """Perform DNS lookup using host command.

        Args:
            domain: Domain to lookup
            record_type: DNS record type (A, AAAA, MX, TXT, etc.)

        Returns:
            List of Content objects with host results
        """
        try:
            if not self._validate_host(domain):
                raise ValueError("Invalid domain provided")

            command = ['host', '-t', record_type, domain]
            result = self._execute_command(command, 30)
            
            response_data = {
                "domain": domain,
                "record_type": record_type,
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "return_code": result["return_code"]
            }
            
            return self._format_response(response_data, "host_lookup")
            
        except Exception as e:
            return self._handle_error("host lookup", e)
