"""
Network connectivity testing tools for NetOps MCP.
"""

from typing import List

from mcp.types import TextContent as Content

from ...formatting.output_parser import OutputParser
from ..base import NetOpsTool


class ConnectivityTools(NetOpsTool):
    """Tools for network connectivity testing."""

    def ping_host(self, host: str, count: int = 4, timeout: int = 10) -> List[Content]:
        """Ping a host to test connectivity.

        Args:
            host: Target host
            count: Number of ping packets
            timeout: Timeout in seconds

        Returns:
            List of Content objects with ping results
        """
        try:
            if not self._validate_host(host):
                raise ValueError("Invalid host provided")

            command = ['ping', '-c', str(count), '-W', str(timeout), host]
            result = self._execute_command(command, timeout + 5)
            
            if 'packets transmitted' in result["stdout"]:
                # Parse ping output whenever a stats block is present,
                # regardless of exit code (unreachable hosts exit 1 but
                # still print full statistics — BUG-01 locked decision).
                ping_stats = OutputParser.parse_ping_output(result["stdout"])
                response_data = {
                    "host": host,
                    "success": result["success"],
                    "stats": ping_stats,
                    "raw_output": result["stdout"]
                }
            else:
                response_data = {
                    "host": host,
                    "success": False,
                    "error": result["stderr"],
                    "raw_output": result["stdout"]
                }
            
            return self._format_response(response_data, "ping_host")
            
        except Exception as e:
            return self._handle_error("ping host", e)

    def traceroute_path(self, target: str, max_hops: int = 30, timeout: int = 30) -> List[Content]:
        """Perform traceroute to a target.

        Args:
            target: Target host
            max_hops: Maximum number of hops
            timeout: Timeout in seconds

        Returns:
            List of Content objects with traceroute results
        """
        try:
            if not self._validate_host(target):
                raise ValueError("Invalid target provided")

            command = ['traceroute', '-m', str(max_hops), '-w', str(timeout), target]
            result = self._execute_command(command, timeout + 10)
            
            if result["success"]:
                # Parse traceroute output
                hops = OutputParser.parse_traceroute_output(result["stdout"])
                response_data = {
                    "target": target,
                    "success": True,
                    "hops": hops,
                    "raw_output": result["stdout"]
                }
            else:
                response_data = {
                    "target": target,
                    "success": False,
                    "error": result["stderr"],
                    "raw_output": result["stdout"]
                }
            
            return self._format_response(response_data, "traceroute_path")
            
        except Exception as e:
            return self._handle_error("traceroute path", e)

    def mtr_monitor(self, target: str, count: int = 10, timeout: int = 30) -> List[Content]:
        """Monitor network path using mtr.

        Args:
            target: Target host
            count: Number of probes
            timeout: Timeout in seconds

        Returns:
            List of Content objects with mtr results
        """
        try:
            if not self._validate_host(target):
                raise ValueError("Invalid target provided")

            # BUG-04: mtr's `-w` is `--report-wide` (takes no argument) — the
            # timeout must never be placed in argv (mtr would probe it as an
            # extra target host). The overall deadline is enforced by the
            # subprocess timeout passed to _execute_command below.
            command = ['mtr', '-c', str(count), '--report', target]
            result = self._execute_command(command, timeout + 10)

            if result["success"]:
                # Parse mtr output
                mtr_stats = OutputParser.parse_mtr_output(result["stdout"])
                response_data = {
                    "target": target,
                    "success": True,
                    "stats": mtr_stats,
                    "raw_output": result["stdout"]
                }
            else:
                response_data = {
                    "target": target,
                    "success": False,
                    "error": result["stderr"],
                    "raw_output": result["stdout"]
                }
            
            return self._format_response(response_data, "mtr_monitor")
            
        except Exception as e:
            return self._handle_error("mtr monitor", e)

    def telnet_connect(self, host: str, port: int, timeout: int = 10) -> List[Content]:
        """Test port connectivity using telnet.

        Args:
            host: Target host
            port: Target port
            timeout: Timeout in seconds

        Returns:
            List of Content objects with telnet results
        """
        try:
            if not self._validate_host(host):
                raise ValueError("Invalid host provided")
            if not self._validate_port(port):
                raise ValueError("Invalid port provided")

            command = ['timeout', str(timeout), 'telnet', host, str(port)]
            result = self._execute_command(command, timeout + 5)
            
            response_data = {
                "host": host,
                "port": port,
                "success": result["success"],
                "connected": result["success"],
                "raw_output": result["stdout"],
                "error": result["stderr"] if not result["success"] else None
            }
            
            return self._format_response(response_data, "telnet_connect")
            
        except Exception as e:
            return self._handle_error("telnet connect", e)

    def netcat_test(self, host: str, port: int, timeout: int = 10) -> List[Content]:
        """Test port connectivity using netcat.

        Args:
            host: Target host
            port: Target port
            timeout: Timeout in seconds

        Returns:
            List of Content objects with netcat results
        """
        try:
            if not self._validate_host(host):
                raise ValueError("Invalid host provided")
            if not self._validate_port(port):
                raise ValueError("Invalid port provided")

            command = ['nc', '-z', '-w', str(timeout), host, str(port)]
            result = self._execute_command(command, timeout + 5)
            
            response_data = {
                "host": host,
                "port": port,
                "success": result["success"],
                "connected": result["success"],
                "raw_output": result["stdout"],
                "error": result["stderr"] if not result["success"] else None
            }
            
            return self._format_response(response_data, "netcat_test")

        except Exception as e:
            return self._handle_error("netcat test", e)
