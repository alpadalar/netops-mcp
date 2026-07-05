"""
DNS tools for NetOps MCP.
"""

from typing import List, Optional

from mcp.types import TextContent as Content

from ..base import NetOpsTool


class DNSTools(NetOpsTool):
    """Tools for DNS operations and queries."""

    def _validate_domain(self, domain: str) -> bool:
        """Validate the queried domain's FORMAT via the central validator (REF-02).

        The domain being *queried* is DATA — you are literally asking DNS to
        resolve it — so it is format-only and is NEVER SSRF-classified (that
        would break "what does X resolve to?" and the DNS-rebind fixture). Keeps
        the historical ``-> bool`` contract.

        Args:
            domain: Domain to validate

        Returns:
            True if the domain is a well-formed name
        """
        from ...validators.input_validator import ValidationError, validate_domain

        try:
            validate_domain(domain)
            return True
        except ValidationError:
            return False

    def _validate_record_type(self, record_type: str) -> bool:
        """Validate DNS record type.

        Args:
            record_type: DNS record type to validate

        Returns:
            True if record type is valid
        """
        if not record_type or not isinstance(record_type, str):
            return False

        valid_record_types = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "PTR", "SOA", "SRV", "CAA"]
        return record_type.upper() in valid_record_types

    def _validate_dns_server(self, server: str) -> bool:
        """Validate the DNS server FORMAT (IP literal or hostname) via the
        central validators (REF-02). Keeps the ``-> bool`` contract.

        The server is the resolver *connection target*, so it is additionally
        SSRF-classified by ``_enforce_ssrf`` in the query methods — this method
        stays format-only.

        Args:
            server: DNS server to validate

        Returns:
            True if the server is a valid IP literal or hostname
        """
        from ...validators.input_validator import (
            ValidationError,
            validate_hostname,
            validate_ip_address,
        )

        try:
            validate_ip_address(server)
            return True
        except ValidationError:
            pass
        try:
            validate_hostname(server)
            return True
        except ValidationError:
            return False

    def nslookup_query(
        self, domain: str, record_type: str = "A", server: Optional[str] = None
    ) -> List[Content]:
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
            if server:
                # SEC-03: the resolver server is a connection target ->
                # SSRF-classify it (non-HTTP fail-open on resolution failure).
                # The queried `domain` above is DATA and is NOT classified.
                self._enforce_ssrf(server)

            command = ["nslookup", "-type=" + record_type, domain]
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
                "return_code": result["return_code"],
            }

            return self._format_response(response_data, "nslookup_query")

        except Exception as e:
            return self._handle_error("nslookup query", e)

    def dig_query(
        self, domain: str, record_type: str = "A", server: Optional[str] = None
    ) -> List[Content]:
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
            if server:
                # SEC-03: the resolver server is a connection target ->
                # SSRF-classify it (non-HTTP fail-open on resolution failure).
                # The queried `domain` above is DATA and is NOT classified.
                self._enforce_ssrf(server)

            command = ["dig", "+short", record_type, domain]
            if server:
                command.extend(["@" + server])

            result = self._execute_command(command, 30)

            response_data = {
                "domain": domain,
                "record_type": record_type,
                "server": server,
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "return_code": result["return_code"],
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

            command = ["host", "-t", record_type, domain]
            result = self._execute_command(command, 30)

            response_data = {
                "domain": domain,
                "record_type": record_type,
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "return_code": result["return_code"],
            }

            return self._format_response(response_data, "host_lookup")

        except Exception as e:
            return self._handle_error("host lookup", e)
