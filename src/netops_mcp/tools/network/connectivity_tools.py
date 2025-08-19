"""
Network connectivity testing tools for DevOps MCP.
"""

import re
from typing import Dict, List, Optional
from mcp.types import TextContent as Content
from ..base import DevOpsTool


class ConnectivityTools(DevOpsTool):
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
            
            if result["success"]:
                # Parse ping output
                ping_stats = self._parse_ping_output(result["stdout"])
                response_data = {
                    "host": host,
                    "success": True,
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
                hops = self._parse_traceroute_output(result["stdout"])
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

            command = ['mtr', '-c', str(count), '-w', str(timeout), '--report', target]
            result = self._execute_command(command, timeout + 10)
            
            if result["success"]:
                # Parse mtr output
                mtr_stats = self._parse_mtr_output(result["stdout"])
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

    def _parse_ping_output(self, output: str) -> Dict[str, any]:
        """Parse ping command output.

        Args:
            output: Raw ping output

        Returns:
            Dictionary with parsed ping statistics
        """
        stats = {
            "packets_transmitted": 0,
            "packets_received": 0,
            "packet_loss_percent": 0,
            "min_rtt": 0,
            "avg_rtt": 0,
            "max_rtt": 0,
            "mdev_rtt": 0
        }
        
        # Parse ping statistics
        lines = output.split('\n')
        for line in lines:
            if 'packets transmitted' in line:
                match = re.search(r'(\d+) packets transmitted, (\d+) received', line)
                if match:
                    stats["packets_transmitted"] = int(match.group(1))
                    stats["packets_received"] = int(match.group(2))
                    stats["packet_loss_percent"] = 100 - (stats["packets_received"] / stats["packets_transmitted"] * 100)
            
            elif 'rtt min/avg/max/mdev' in line:
                match = re.search(r'(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*)', line)
                if match:
                    stats["min_rtt"] = float(match.group(1))
                    stats["avg_rtt"] = float(match.group(2))
                    stats["max_rtt"] = float(match.group(3))
                    stats["mdev_rtt"] = float(match.group(4))
        
        return stats

    def _parse_traceroute_output(self, output: str) -> List[Dict[str, any]]:
        """Parse traceroute command output.

        Args:
            output: Raw traceroute output

        Returns:
            List of hop information
        """
        hops = []
        lines = output.split('\n')
        
        for line in lines:
            if line.strip() and not line.startswith('traceroute'):
                # Parse hop line
                parts = line.split()
                if len(parts) >= 4:
                    hop_info = {
                        "hop_number": int(parts[0]),
                        "host": parts[1],
                        "ip": parts[1],
                        "times": []
                    }
                    
                    # Extract response times
                    for part in parts[2:]:
                        if part != '*':
                            try:
                                hop_info["times"].append(float(part))
                            except ValueError:
                                pass
                    
                    hops.append(hop_info)
        
        return hops

    def _parse_mtr_output(self, output: str) -> Dict[str, any]:
        """Parse mtr command output.

        Args:
            output: Raw mtr output

        Returns:
            Dictionary with mtr statistics
        """
        stats = {
            "target": "",
            "hops": []
        }
        
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('Start') or line.startswith('HOST:'):
                continue
                
            parts = line.split()
            if len(parts) >= 8:
                try:
                    # Skip header lines and non-numeric entries
                    hop_num = int(parts[0])
                    hop_info = {
                        "hop": hop_num,
                        "host": parts[1],
                        "loss_percent": float(parts[2].rstrip('%')),
                        "snt": int(parts[3]),
                        "last": float(parts[4]),
                        "avg": float(parts[5]),
                        "best": float(parts[6]),
                        "worst": float(parts[7])
                    }
                    stats["hops"].append(hop_info)
                except (ValueError, IndexError):
                    # Skip malformed lines
                    continue
        
        return stats
