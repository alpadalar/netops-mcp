"""
DNS tools for NetOps MCP.
"""

import re
from typing import Dict, List, Optional
from mcp.types import TextContent as Content
from ..base import NetOpsTool


class DNSTools(NetOpsTool):
    """Tools for DNS operations and queries."""

    def _validate_domain(self, domain: str) -> bool:
        """Validate domain name format.

        Args:
            domain: Domain to validate

        Returns:
            True if domain is valid
        """
        if not domain or not isinstance(domain, str):
            return False
        
        # Basic domain validation regex
        domain_pattern = re.compile(
            r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
        )
        
        return bool(domain_pattern.match(domain))

    def _validate_record_type(self, record_type: str) -> bool:
        """Validate DNS record type.

        Args:
            record_type: DNS record type to validate

        Returns:
            True if record type is valid
        """
        if not record_type or not isinstance(record_type, str):
            return False
        
        valid_record_types = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME', 'PTR', 'SOA', 'SRV', 'CAA']
        return record_type.upper() in valid_record_types

    def _validate_dns_server(self, server: str) -> bool:
        """Validate DNS server address.

        Args:
            server: DNS server to validate

        Returns:
            True if DNS server is valid
        """
        if not server or not isinstance(server, str):
            return False
        
        # Check if it's a valid IP address
        ip_pattern = re.compile(
            r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        )
        
        # Check if it's a valid domain name
        domain_pattern = re.compile(
            r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
        )
        
        return bool(ip_pattern.match(server) or domain_pattern.match(server))

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
            if not self._validate_domain(domain):
                raise ValueError("Invalid domain provided")
            
            if not self._validate_record_type(record_type):
                raise ValueError("Invalid record type provided")
            
            if server and not self._validate_dns_server(server):
                raise ValueError("Invalid DNS server provided")

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
            if not self._validate_domain(domain):
                raise ValueError("Invalid domain provided")
            
            if not self._validate_record_type(record_type):
                raise ValueError("Invalid record type provided")
            
            if server and not self._validate_dns_server(server):
                raise ValueError("Invalid DNS server provided")

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
            if not self._validate_domain(domain):
                raise ValueError("Invalid domain provided")
            
            if not self._validate_record_type(record_type):
                raise ValueError("Invalid record type provided")

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
