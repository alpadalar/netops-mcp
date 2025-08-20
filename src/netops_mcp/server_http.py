"""
HTTP-based MCP server implementation for NetOpsMCP.

This module provides an HTTP transport layer for the MCP server,
supporting both regular HTTP and streamable HTTP transports.
"""

import logging
import json
import os
import sys
import signal
from typing import Optional

try:
    from fastmcp import FastMCP
    FASTMCP_AVAILABLE = True
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
        FASTMCP_AVAILABLE = True
    except ImportError:
        FASTMCP_AVAILABLE = False

from .config.loader import load_config
from .core.logging import setup_logging
from .tools.network.http_tools import HTTPTools
from .tools.network.connectivity_tools import ConnectivityTools
from .tools.network.dns_tools import DNSTools
from .tools.network.discovery_tools import DiscoveryTools
from .tools.system.network_tools import NetworkTools
from .tools.system.monitoring_tools import MonitoringTools
from .tools.security.scanning_tools import ScanningTools
from .utils.system_check import check_required_tools, get_system_info


logger = logging.getLogger("netops-mcp.http")


class NetOpsMCPHTTPServer:
    """
    HTTP-based MCP server for network operations tools.
    
    This server supports:
    - Streamable HTTP transport
    - Comprehensive network operations toolset
    - Real-time network diagnostics
    - System monitoring capabilities
    """
    
    def __init__(self, 
                 config_path: Optional[str] = None,
                 host: str = "0.0.0.0",
                 port: int = 8815,
                 path: str = "/netops-mcp"):
        """
        Initialize the HTTP MCP server.
        
        Args:
            config_path: Path to configuration file
            host: Server host address
            port: Server port
            path: HTTP path for MCP endpoint
        """
        if not FASTMCP_AVAILABLE:
            raise RuntimeError("FastMCP is not available. Please install fastmcp package.")
            
        self.config = load_config(config_path)
        self.logger = setup_logging(self.config.logging)
        self.host = host
        self.port = port
        self.path = path
        
        # Initialize tools
        self.http_tools = HTTPTools()
        self.connectivity_tools = ConnectivityTools()
        self.dns_tools = DNSTools()
        self.discovery_tools = DiscoveryTools()
        self.network_tools = NetworkTools()
        self.monitoring_tools = MonitoringTools()
        self.scanning_tools = ScanningTools()
        
        # Initialize FastMCP
        self.mcp = FastMCP("NetOpsMCP-HTTP")
        
        # Add health check endpoint
        self._setup_health_check()
        
        # Setup tools
        self._setup_tools()

    def _setup_tools(self) -> None:
        """Register MCP tools with the server."""
        
        # HTTP/API Testing Tools
        @self.mcp.tool(description="Execute HTTP request using curl")
        def curl_request(url: str, method: str = "GET", headers: Optional[dict] = None, 
                        data: Optional[str] = None, timeout: int = 30):
            return self.http_tools.curl_request(url, method, headers, data, timeout)

        @self.mcp.tool(description="Execute HTTP request using httpie")
        def httpie_request(url: str, method: str = "GET", headers: Optional[dict] = None,
                          data: Optional[dict] = None, timeout: int = 30):
            return self.http_tools.httpie_request(url, method, headers, data, timeout)

        @self.mcp.tool(description="Test API endpoint with validation")
        def api_test(url: str, method: str = "GET", expected_status: int = 200,
                    headers: Optional[dict] = None, timeout: int = 30):
            return self.http_tools.api_test(url, method, expected_status, headers, timeout)

        # Network Connectivity Tools
        @self.mcp.tool(description="Ping a host to test connectivity")
        def ping_host(host: str, count: int = 4, timeout: int = 10):
            return self.connectivity_tools.ping_host(host, count, timeout)

        @self.mcp.tool(description="Perform traceroute to a target")
        def traceroute_path(target: str, max_hops: int = 30, timeout: int = 30):
            return self.connectivity_tools.traceroute_path(target, max_hops, timeout)

        @self.mcp.tool(description="Monitor network path using mtr")
        def mtr_monitor(target: str, count: int = 10, timeout: int = 30):
            return self.connectivity_tools.mtr_monitor(target, count, timeout)

        @self.mcp.tool(description="Test port connectivity using telnet")
        def telnet_connect(host: str, port: int, timeout: int = 10):
            return self.connectivity_tools.telnet_connect(host, port, timeout)

        @self.mcp.tool(description="Test port connectivity using netcat")
        def netcat_test(host: str, port: int, timeout: int = 10):
            return self.connectivity_tools.netcat_test(host, port, timeout)

        # DNS Tools
        @self.mcp.tool(description="Perform DNS lookup using nslookup")
        def nslookup_query(domain: str, record_type: str = "A", server: Optional[str] = None):
            return self.dns_tools.nslookup_query(domain, record_type, server)

        @self.mcp.tool(description="Perform DNS lookup using dig")
        def dig_query(domain: str, record_type: str = "A", server: Optional[str] = None):
            return self.dns_tools.dig_query(domain, record_type, server)

        @self.mcp.tool(description="Perform DNS lookup using host")
        def host_lookup(domain: str, record_type: str = "A"):
            return self.dns_tools.host_lookup(domain, record_type)

        # Network Discovery Tools
        @self.mcp.tool(description="Scan network using nmap")
        def nmap_scan(target: str, ports: Optional[str] = None, scan_type: str = "basic", timeout: int = 300):
            return self.discovery_tools.nmap_scan(target, ports, scan_type, timeout)

        @self.mcp.tool(description="Discover network services")
        def service_discovery(target: str, ports: Optional[str] = None):
            return self.discovery_tools.service_discovery(target, ports)

        # System Network Tools
        @self.mcp.tool(description="Show network connections using ss")
        def ss_connections(state: Optional[str] = None, protocol: Optional[str] = None):
            return self.network_tools.ss_connections(state, protocol)

        @self.mcp.tool(description="Show network connections using netstat")
        def netstat_connections(state: Optional[str] = None, protocol: Optional[str] = None):
            return self.network_tools.netstat_connections(state, protocol)

        @self.mcp.tool(description="Show ARP table")
        def arp_table():
            return self.network_tools.arp_table()

        @self.mcp.tool(description="ARP ping a host")
        def arping_host(host: str, count: int = 4):
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
        def process_list(limit: int = 20):
            return self.monitoring_tools.process_list(limit)

        # Security Tools
        @self.mcp.tool(description="Scan ports on a target")
        def port_scan(target: str, ports: str, timeout: int = 60):
            return self.scanning_tools.port_scan(target, ports, timeout)

        @self.mcp.tool(description="Enumerate services on a target")
        def service_enumeration(target: str, ports: Optional[str] = None):
            return self.scanning_tools.service_enumeration(target, ports)

        # System Tools
        @self.mcp.tool(description="Check required system tools")
        def check_required_tools():
            try:
                tools = check_required_tools()
                system_info = get_system_info()
                
                response_data = {
                    "tools": tools,
                    "system_info": system_info,
                    "missing_tools": [tool for tool, available in tools.items() if not available]
                }
                
                return [{"type": "text", "text": json.dumps(response_data, indent=2)}]
            except Exception as e:
                return [{"type": "text", "text": json.dumps({"error": str(e)}, indent=2)}]

        @self.mcp.tool(description="Health check endpoint")
        def health():
            # Count MCP tools (26 total)
            mcp_tools = [
                # HTTP/API Testing Tools (3)
                "curl_request", "httpie_request", "api_test",
                # Network Connectivity Tools (5)
                "ping_host", "traceroute_path", "mtr_monitor", "telnet_connect", "netcat_test",
                # DNS Tools (3)
                "nslookup_query", "dig_query", "host_lookup",
                # Network Discovery Tools (2)
                "nmap_scan", "service_discovery",
                # System Network Tools (4)
                "ss_connections", "netstat_connections", "arp_table", "arping_host",
                # System Monitoring Tools (5)
                "system_status", "cpu_usage", "memory_usage", "disk_usage", "process_list",
                # Security Tools (2)
                "port_scan", "service_enumeration",
                # System Tools (2)
                "check_required_tools", "health"
            ]
            
            # Count system tools
            system_tools = check_required_tools()
            available_system_tools = len(system_tools['available_tools'])
            total_system_tools = len(system_tools['available_tools']) + len(system_tools['missing_tools'])
            
            return [{"type": "text", "text": json.dumps({
                "status": "ok",
                "server": "NetOpsMCP-HTTP",
                "mcp_tools": len(mcp_tools),
                "system_tools_available": available_system_tools,
                "system_tools_total": total_system_tools,
                "total_tools": len(mcp_tools) + total_system_tools
            })}]

    def _setup_health_check(self):
        """Setup health check endpoint for Docker."""
        # FastMCP doesn't expose app directly, so we'll use a different approach
        # We'll create a simple health check file that can be checked
        import os
        import time
        
        health_file = "/tmp/netops-mcp-health"
        
        # Create a simple health check function
        def update_health_status():
            try:
                # Count MCP tools (26 total)
                mcp_tools = [
                    # HTTP/API Testing Tools (3)
                    "curl_request", "httpie_request", "api_test",
                    # Network Connectivity Tools (5)
                    "ping_host", "traceroute_path", "mtr_monitor", "telnet_connect", "netcat_test",
                    # DNS Tools (3)
                    "nslookup_query", "dig_query", "host_lookup",
                    # Network Discovery Tools (2)
                    "nmap_scan", "service_discovery",
                    # System Network Tools (4)
                    "ss_connections", "netstat_connections", "arp_table", "arping_host",
                    # System Monitoring Tools (5)
                    "system_status", "cpu_usage", "memory_usage", "disk_usage", "process_list",
                    # Security Tools (2)
                    "port_scan", "service_enumeration",
                    # System Tools (2)
                    "check_required_tools", "health"
                ]
                
                # Count system tools
                system_tools = check_required_tools()
                available_system_tools = len(system_tools['available_tools'])
                total_system_tools = len(system_tools['available_tools']) + len(system_tools['missing_tools'])
                
                health_data = {
                    "status": "healthy",
                    "server": "NetOpsMCP-HTTP",
                    "mcp_tools": len(mcp_tools),
                    "system_tools_available": available_system_tools,
                    "system_tools_total": total_system_tools,
                    "total_tools": len(mcp_tools) + total_system_tools,
                    "timestamp": time.time()
                }
                
                with open(health_file, 'w') as f:
                    json.dump(health_data, f)
                    
            except Exception as e:
                health_data = {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": time.time()
                }
                
                with open(health_file, 'w') as f:
                    json.dump(health_data, f)
        
        # Update health status every 30 seconds
        import threading
        
        def health_check_loop():
            while True:
                update_health_status()
                time.sleep(30)
        
        # Start health check thread
        health_thread = threading.Thread(target=health_check_loop, daemon=True)
        health_thread.start()

    def run(self) -> None:
        """
        Start the HTTP MCP server.
        
        Runs the server with streamable HTTP transport on the configured
        host and port.
        """
        def signal_handler(signum, frame):
            self.logger.info("Received signal to shutdown HTTP server...")
            sys.exit(0)

        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            self.logger.info(f"Starting NetOpsMCP HTTP server on {self.host}:{self.port}{self.path}")
            
            # Run with FastMCP's built-in HTTP transport
            self.mcp.run(
                transport="http",
                host=self.host,
                port=self.port,
                path=self.path
            )
        except Exception as e:
            self.logger.error(f"HTTP server error: {e}")
            sys.exit(1)


def main():
    """Main entry point for standalone execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='NetOpsMCP HTTP Server')
    parser.add_argument('--host', default='0.0.0.0', help='Server host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8815, help='Server port (default: 8815)')
    parser.add_argument('--path', default='/netops-mcp', help='HTTP path (default: /netops-mcp)')
    parser.add_argument('--config', help='Configuration file path')
    
    args = parser.parse_args()
    
    try:
        server = NetOpsMCPHTTPServer(
            config_path=args.config,
            host=args.host,
            port=args.port,
            path=args.path
        )
        
        server.run()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
