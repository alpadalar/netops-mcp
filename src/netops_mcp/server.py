"""
Main server implementation for NetOps MCP.

This module implements the core MCP server for network operations and diagnostic tools, providing:
- Configuration loading and validation
- Logging setup
- MCP tool registration and routing
- Signal handling for graceful shutdown

The server exposes a comprehensive set of tools for network operations including:
- Network diagnostic tools (ping, traceroute, nmap, curl, etc.)
- System administration tools (ss, netstat, arp, etc.)
- Security tools (port scanning, service discovery)
- Monitoring tools (system status, resource usage)
"""

import logging
import json
import os
import sys
import signal
from typing import Optional, List, Annotated

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.tools import Tool
from mcp.types import TextContent as Content
from pydantic import Field

from .config.loader import load_config
from .core.logging import setup_logging
from .tools.network.http_tools import HTTPTools
from .tools.network.connectivity_tools import ConnectivityTools
from .tools.network.dns_tools import DNSTools
from .tools.network.discovery_tools import DiscoveryTools
from .tools.system.network_tools import NetworkTools
from .tools.system.monitoring_tools import MonitoringTools
from .tools.security.scanning_tools import ScanningTools
from .utils.system_check import check_required_tools as check_tools_status, get_system_info


class NetOpsMCPServer:
    """Main server class for NetOps MCP."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the server.

        Args:
            config_path: Path to configuration file
        """
        # Load and validate configuration
        self.config = load_config(config_path)
        
        # Setup logging
        self.logger = setup_logging(self.config.logging)
        
        # Test system requirements on startup
        self._test_system_requirements()
        
        # Initialize tools
        self.http_tools = HTTPTools()
        self.connectivity_tools = ConnectivityTools()
        self.dns_tools = DNSTools()
        self.discovery_tools = DiscoveryTools()
        self.network_tools = NetworkTools()
        self.monitoring_tools = MonitoringTools()
        self.scanning_tools = ScanningTools()
        
        # Initialize MCP server
        self.mcp = FastMCP("NetOpsMCP")
        self._tests_passed: Optional[bool] = None
        self._setup_tools()

    def _test_system_requirements(self) -> None:
        """Test system requirements and required tools."""
        try:
            self.logger.info("Testing system requirements...")
            
            # Check required tools
            tool_status = check_tools_status()
            missing_tools = [tool for tool, available in tool_status.items() if not available]
            
            if missing_tools:
                self.logger.warning(f"Missing tools: {', '.join(missing_tools)}")
            else:
                self.logger.info("All required tools are available")
            
            # Get system info
            system_info = get_system_info()
            self.logger.info(f"System: {system_info['platform']} {system_info['platform_version']}")
            self.logger.info(f"Python: {system_info['python_version']}")
            self.logger.info(f"CPU: {system_info['cpu_count']} cores")
            self.logger.info(f"Memory: {system_info['memory_total']}")
            
        except Exception as e:
            self.logger.error(f"System requirements test failed: {e}")

    def _setup_tools(self) -> None:
        """Register MCP tools with the server."""
        
        # HTTP/API Testing Tools
        @self.mcp.tool(description="Execute HTTP request using curl")
        def curl_request(
            url: Annotated[str, Field(description="Target URL")],
            method: Annotated[str, Field(description="HTTP method", default="GET")] = "GET",
            headers: Annotated[Optional[dict], Field(description="HTTP headers")] = None,
            data: Annotated[Optional[str], Field(description="Request body")] = None,
            timeout: Annotated[int, Field(description="Timeout in seconds", default=30)] = 30
        ):
            return self.http_tools.curl_request(url, method, headers, data, timeout)

        @self.mcp.tool(description="Execute HTTP request using httpie")
        def httpie_request(
            url: Annotated[str, Field(description="Target URL")],
            method: Annotated[str, Field(description="HTTP method", default="GET")] = "GET",
            headers: Annotated[Optional[dict], Field(description="HTTP headers")] = None,
            data: Annotated[Optional[dict], Field(description="Request data")] = None,
            timeout: Annotated[int, Field(description="Timeout in seconds", default=30)] = 30
        ):
            return self.http_tools.httpie_request(url, method, headers, data, timeout)

        @self.mcp.tool(description="Test API endpoint with validation")
        def api_test(
            url: Annotated[str, Field(description="API endpoint URL")],
            method: Annotated[str, Field(description="HTTP method", default="GET")] = "GET",
            expected_status: Annotated[int, Field(description="Expected HTTP status", default=200)] = 200,
            headers: Annotated[Optional[dict], Field(description="HTTP headers")] = None,
            timeout: Annotated[int, Field(description="Timeout in seconds", default=30)] = 30
        ):
            return self.http_tools.api_test(url, method, expected_status, headers, timeout)

        # Network Connectivity Tools
        @self.mcp.tool(description="Ping a host to test connectivity")
        def ping_host(
            host: Annotated[str, Field(description="Target host")],
            count: Annotated[int, Field(description="Number of ping packets", default=4)] = 4,
            timeout: Annotated[int, Field(description="Timeout in seconds", default=10)] = 10
        ):
            return self.connectivity_tools.ping_host(host, count, timeout)

        @self.mcp.tool(description="Perform traceroute to a target")
        def traceroute_path(
            target: Annotated[str, Field(description="Target host")],
            max_hops: Annotated[int, Field(description="Maximum number of hops", default=30)] = 30,
            timeout: Annotated[int, Field(description="Timeout in seconds", default=30)] = 30
        ):
            return self.connectivity_tools.traceroute_path(target, max_hops, timeout)

        @self.mcp.tool(description="Monitor network path using mtr")
        def mtr_monitor(
            target: Annotated[str, Field(description="Target host")],
            count: Annotated[int, Field(description="Number of probes", default=10)] = 10,
            timeout: Annotated[int, Field(description="Timeout in seconds", default=30)] = 30
        ):
            return self.connectivity_tools.mtr_monitor(target, count, timeout)

        @self.mcp.tool(description="Test port connectivity using telnet")
        def telnet_connect(
            host: Annotated[str, Field(description="Target host")],
            port: Annotated[int, Field(description="Target port")],
            timeout: Annotated[int, Field(description="Timeout in seconds", default=10)] = 10
        ):
            return self.connectivity_tools.telnet_connect(host, port, timeout)

        @self.mcp.tool(description="Test port connectivity using netcat")
        def netcat_test(
            host: Annotated[str, Field(description="Target host")],
            port: Annotated[int, Field(description="Target port")],
            timeout: Annotated[int, Field(description="Timeout in seconds", default=10)] = 10
        ):
            return self.connectivity_tools.netcat_test(host, port, timeout)

        # DNS Tools
        @self.mcp.tool(description="Perform DNS lookup using nslookup")
        def nslookup_query(
            domain: Annotated[str, Field(description="Domain to lookup")],
            record_type: Annotated[str, Field(description="DNS record type", default="A")] = "A",
            server: Annotated[Optional[str], Field(description="DNS server")] = None
        ):
            return self.dns_tools.nslookup_query(domain, record_type, server)

        @self.mcp.tool(description="Perform DNS lookup using dig")
        def dig_query(
            domain: Annotated[str, Field(description="Domain to lookup")],
            record_type: Annotated[str, Field(description="DNS record type", default="A")] = "A",
            server: Annotated[Optional[str], Field(description="DNS server")] = None
        ):
            return self.dns_tools.dig_query(domain, record_type, server)

        @self.mcp.tool(description="Perform DNS lookup using host")
        def host_lookup(
            domain: Annotated[str, Field(description="Domain to lookup")],
            record_type: Annotated[str, Field(description="DNS record type", default="A")] = "A"
        ):
            return self.dns_tools.host_lookup(domain, record_type)

        # Network Discovery Tools
        @self.mcp.tool(description="Scan network using nmap")
        def nmap_scan(
            target: Annotated[str, Field(description="Target host or network")],
            ports: Annotated[Optional[str], Field(description="Port range (e.g., '22,80,443')")] = None,
            scan_type: Annotated[str, Field(description="Scan type", default="basic")] = "basic",
            timeout: Annotated[int, Field(description="Timeout in seconds", default=300)] = 300
        ):
            return self.discovery_tools.nmap_scan(target, ports, scan_type, timeout)

        @self.mcp.tool(description="Discover network services")
        def service_discovery(
            target: Annotated[str, Field(description="Target host")],
            ports: Annotated[Optional[str], Field(description="Port range")] = None
        ):
            return self.discovery_tools.service_discovery(target, ports)

        # System Network Tools
        @self.mcp.tool(description="Show network connections using ss")
        def ss_connections(
            state: Annotated[Optional[str], Field(description="Connection state")] = None,
            protocol: Annotated[Optional[str], Field(description="Protocol (tcp/udp)")] = None
        ):
            return self.network_tools.ss_connections(state, protocol)

        @self.mcp.tool(description="Show network connections using netstat")
        def netstat_connections(
            state: Annotated[Optional[str], Field(description="Connection state")] = None,
            protocol: Annotated[Optional[str], Field(description="Protocol (tcp/udp)")] = None
        ):
            return self.network_tools.netstat_connections(state, protocol)

        @self.mcp.tool(description="Show ARP table")
        def arp_table():
            return self.network_tools.arp_table()

        @self.mcp.tool(description="ARP ping a host")
        def arping_host(
            host: Annotated[str, Field(description="Target host")],
            count: Annotated[int, Field(description="Number of packets", default=4)] = 4
        ):
            return self.network_tools.arping_host(host, count)

        # System Monitoring Tools
        @self.mcp.tool(description="Get system status")
        def system_status():
            return self.monitoring_tools.system_status()

        @self.mcp.tool(description="Get CPU usage information")
        def cpu_usage():
            return self.monitoring_tools.cpu_usage()

        @self.mcp.tool(description="Get memory usage information")
        def memory_usage():
            return self.monitoring_tools.memory_usage()

        @self.mcp.tool(description="Get disk usage information")
        def disk_usage():
            return self.monitoring_tools.disk_usage()

        @self.mcp.tool(description="List running processes")
        def process_list(
            limit: Annotated[int, Field(description="Number of processes to show", default=20)] = 20
        ):
            return self.monitoring_tools.process_list(limit)

        # Security Tools
        @self.mcp.tool(description="Scan ports on a target")
        def port_scan(
            target: Annotated[str, Field(description="Target host")],
            ports: Annotated[str, Field(description="Port range (e.g., '1-1000')")],
            timeout: Annotated[int, Field(description="Timeout in seconds", default=60)] = 60
        ):
            return self.scanning_tools.port_scan(target, ports, timeout)

        @self.mcp.tool(description="Enumerate services on a target")
        def service_enumeration(
            target: Annotated[str, Field(description="Target host")],
            ports: Annotated[Optional[str], Field(description="Port range")] = None
        ):
            return self.scanning_tools.service_enumeration(target, ports)

        # System Tools
        @self.mcp.tool(description="Check required system tools")
        def check_required_tools():
            tools = check_tools_status()
            system_info = get_system_info()
            
            response_data = {
                "tools": tools,
                "system_info": system_info,
                "missing_tools": [tool for tool, available in tools.items() if not available]
            }
            
            return [Content(type="text", text=json.dumps(response_data, indent=2))]

        @self.mcp.tool(description="Health check endpoint")
        def health():
            status = "ok" if self._tests_passed is True else ("degraded" if self._tests_passed is False else "unknown")
            return [Content(type="text", text=json.dumps({
                "status": status,
                "tests_passed": self._tests_passed,
                "details": "Startup tests passed" if self._tests_passed else ("Startup tests failed" if self._tests_passed is False else "No tests executed")
            }))]

    def start(self) -> None:
        """Start the MCP server."""
        import anyio

        def signal_handler(signum, frame):
            self.logger.info("Received signal to shutdown...")
            sys.exit(0)

        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            # Optionally run tests before serving
            run_tests = os.getenv("RUN_TESTS_ON_START", "0").lower() in ("1", "true", "yes", "on")
            if run_tests:
                import subprocess
                self.logger.info("Running startup tests (pytest)...")
                env = os.environ.copy()
                env["PYTHONPATH"] = f"{os.getcwd()}/src" + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
                result = subprocess.run([sys.executable, "-m", "pytest", "-q"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
                self._tests_passed = (result.returncode == 0)
                if not self._tests_passed:
                    self.logger.error("Startup tests failed. Health will be 'degraded'. Output:\n" + result.stdout.decode())
                else:
                    self.logger.info("Startup tests passed.")

            self.logger.info("Starting NetOps MCP server...")
            anyio.run(self.mcp.run_stdio_async)
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            sys.exit(1)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='NetOps MCP Server')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--test', action='store_true', help='Run system tests and exit')
    
    args = parser.parse_args()
    
    if args.test:
        print("Running system tests...")
        tools = check_tools_status()
        system_info = get_system_info()
        
        print(f"System: {system_info['platform']} {system_info['platform_version']}")
        print(f"Python: {system_info['python_version']}")
        print(f"CPU: {system_info['cpu_count']} cores")
        print(f"Memory: {system_info['memory_total']}")
        
        print("\nRequired tools:")
        for tool, available in tools.items():
            status = "✅" if available else "❌"
            print(f"  {status} {tool}")
        
        missing = [tool for tool, available in tools.items() if not available]
        if missing:
            print(f"\nMissing tools: {', '.join(missing)}")
            sys.exit(1)
        else:
            print("\nAll tools available!")
            sys.exit(0)
    
    try:
        config_path = args.config or os.getenv("NETOPS_MCP_CONFIG")
        server = NetOpsMCPServer(config_path)
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
