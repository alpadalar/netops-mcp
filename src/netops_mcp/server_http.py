"""
HTTP-based MCP server implementation for NetOpsMCP.

This module provides an HTTP transport layer for the MCP server,
supporting both regular HTTP and streamable HTTP transports.
"""

import hashlib
import json
import logging
import os
import secrets
import signal
import sys
import time
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
from .tools.registry import register_tools
from .utils.system_check import check_required_tools as check_tools_status
from .middleware.auth import AuthenticationMiddleware
from .middleware.rate_limiter import RateLimitMiddleware
from .middleware.metrics import MetricsMiddleware, create_metrics_endpoint


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
                 host: Optional[str] = None,
                 port: Optional[int] = None,
                 path: Optional[str] = None):
        """
        Initialize the HTTP MCP server.

        Explicit arguments win over config; omitted (None) arguments fall back
        to config.server values, whose builtin defaults are 0.0.0.0 / 8815 /
        /netops-mcp (CLI > config.server > builtin precedence).

        Args:
            config_path: Path to configuration file
            host: Server host address (default: config server.host or 0.0.0.0)
            port: Server port (default: config server.port or 8815)
            path: HTTP path for MCP endpoint (default: config server.path or /netops-mcp)
        """
        if not FASTMCP_AVAILABLE:
            raise RuntimeError("FastMCP is not available. Please install fastmcp package.")

        self.config = load_config(config_path)
        self.logger = setup_logging(self.config.logging)
        self.host = host if host is not None else self.config.server.host
        self.port = port if port is not None else self.config.server.port
        self.path = path if path is not None else self.config.server.path
        
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

        # Register the shared 26-tool surface (REF-04). tool_count is derived
        # dynamically from the FastMCP instance (REF-05), replacing the former
        # hardcoded 26 in the tool-registration path.
        self.tool_count = register_tools(self.mcp, self)

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
                system_tools = check_tools_status()
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

    def _add_health_endpoint(self):
        """Add custom health endpoint and middleware to FastMCP HTTP transport."""
        try:
            self.logger.info("Attempting to add custom health endpoint and middleware...")
            self.logger.info(f"FastMCP object type: {type(self.mcp)}")
            self.logger.info(f"FastMCP attributes: {dir(self.mcp)}")
            
            # FastMCP HTTP transport'ına custom endpoint ekle
            if hasattr(self.mcp, 'http_app') and callable(self.mcp.http_app):
                self.logger.info("FastMCP http_app method found, getting Starlette app...")
                # Starlette app'i al
                starlette_app = self.mcp.http_app()
                self.logger.info(f"Starlette app type: {type(starlette_app)}")
                
                # Add middleware
                self._add_middleware(starlette_app)
                
                # Starlette app'e health endpoint ekle
                from starlette.responses import JSONResponse
                
                async def health_endpoint(request):
                    try:
                        # System tools kontrolü
                        system_tools = check_tools_status()
                        available_tools = len(system_tools['available_tools'])
                        total_tools = len(system_tools['available_tools']) + len(system_tools['missing_tools'])
                        
                        return JSONResponse({
                            "status": "healthy",
                            "server": "NetOpsMCP-HTTP",
                            "mcp_tools": 26,  # Total MCP tools
                            "system_tools_available": available_tools,
                            "system_tools_total": total_tools,
                            "total_tools": 26 + total_tools,
                            "authentication": self.config.security.require_auth,
                            "rate_limiting": True,
                            "timestamp": time.time()
                        })
                    except Exception as e:
                        return JSONResponse({
                            "status": "unhealthy",
                            "error": str(e),
                            "timestamp": time.time()
                        }, status_code=500)
                
                # Starlette app'e route ekle
                starlette_app.add_route("/health", health_endpoint, methods=["GET"])
                self.logger.info("Custom health endpoint added at /health")
                
                # Add metrics endpoint
                metrics_endpoint_handler = create_metrics_endpoint()
                starlette_app.add_route("/metrics", metrics_endpoint_handler, methods=["GET"])
                self.logger.info("Metrics endpoint added at /metrics")
            else:
                self.logger.warning("FastMCP http_app method not available, using file-based health check")
                self.logger.info(f"Available attributes: {[attr for attr in dir(self.mcp) if not attr.startswith('_')]}")
                
        except Exception as e:
            self.logger.warning(f"Could not add custom health endpoint: {e}")
            self.logger.info("Using file-based health check as fallback")
    
    def _add_middleware(self, app):
        """Add middleware to Starlette app."""
        try:
            # Add metrics middleware (first, so it tracks all requests)
            app.add_middleware(MetricsMiddleware)
            self.logger.info("Metrics middleware enabled")
            
            # Add CORS middleware if enabled
            if self.config.security.enable_cors:
                from starlette.middleware.cors import CORSMiddleware
                app.add_middleware(
                    CORSMiddleware,
                    allow_origins=self.config.security.cors_origins,
                    allow_credentials=self.config.security.cors_allow_credentials,
                    allow_methods=["*"],
                    allow_headers=["*"],
                )
                self.logger.info(f"CORS middleware enabled for origins: {self.config.security.cors_origins}")
            
            # Add rate limiting middleware
            app.add_middleware(
                RateLimitMiddleware,
                requests_per_window=self.config.security.rate_limit_requests,
                window_seconds=self.config.security.rate_limit_window,
                exempt_paths={"/health", "/metrics"}
            )
            self.logger.info(
                f"Rate limiting enabled: {self.config.security.rate_limit_requests} "
                f"requests per {self.config.security.rate_limit_window}s"
            )
            
            # Add authentication middleware if required
            if self.config.security.require_auth:
                if not self.config.security.api_keys:
                    self.logger.warning("Authentication required but no API keys configured!")
                else:
                    app.add_middleware(
                        AuthenticationMiddleware,
                        api_keys=self.config.security.api_keys,
                        require_auth=True,
                        exempt_paths={"/health", "/metrics"}
                    )
                    self.logger.info(f"Authentication enabled with {len(self.config.security.api_keys)} API key(s)")
            
            # Add security headers middleware
            from starlette.middleware.trustedhost import TrustedHostMiddleware
            if self.config.security.allowed_hosts:
                app.add_middleware(
                    TrustedHostMiddleware,
                    allowed_hosts=self.config.security.allowed_hosts
                )
                self.logger.info(f"Trusted host middleware enabled for: {self.config.security.allowed_hosts}")
            
        except Exception as e:
            self.logger.error(f"Error adding middleware: {e}")

    def run(self) -> None:
        """
        Start the HTTP MCP server.

        Runs the server with streamable HTTP transport on the configured
        host and port.

        Raises:
            RuntimeError: If require_auth is enabled (the default) but no
                API keys are configured. The server refuses to start BEFORE
                uvicorn binds; the error carries operator guidance including
                a freshly generated example key (never auto-activated).
        """
        # Fail-fast auth gate (SEC-01): must stay in run(), never __init__,
        # and BEFORE the try block below so the RuntimeError propagates to
        # main() instead of being swallowed by the except handler.
        if self.config.security.require_auth and not self.config.security.api_keys:
            example = secrets.token_urlsafe(32)
            raise RuntimeError(
                "HTTP mode requires an API key (require_auth is enabled by default).\n"
                f"  1. Example key (generated now, save it): {example}\n"
                f"  2. Add its hash to config security.api_keys: "
                f"\"sha256:{hashlib.sha256(example.encode()).hexdigest()}\"\n"
                "  3. Or explicitly opt out: \"require_auth\": false  (NOT recommended)\n"
            )

        def signal_handler(signum, frame):
            self.logger.info("Received signal to shutdown HTTP server...")
            sys.exit(0)

        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            self.logger.info(f"Starting NetOpsMCP HTTP server on {self.host}:{self.port}{self.path}")
            
            # Add custom health endpoint before starting server
            self._add_health_endpoint()
            
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


def main() -> None:
    """Main entry point for standalone execution."""
    import argparse

    parser = argparse.ArgumentParser(description='NetOpsMCP HTTP Server')
    parser.add_argument('--host', default=None,
                        help='Server host (default: config server.host or 0.0.0.0)')
    parser.add_argument('--port', type=int, default=None,
                        help='Server port (default: config server.port or 8815)')
    parser.add_argument('--path', default=None,
                        help='HTTP path (default: config server.path or /netops-mcp)')
    parser.add_argument('--config',
                        help='Configuration file path (default: $NETOPS_MCP_CONFIG)')

    args = parser.parse_args()

    # Parity with the stdio server: fall back to NETOPS_MCP_CONFIG when
    # --config is omitted (start_http_server.sh exports it either way).
    config_path = args.config or os.getenv("NETOPS_MCP_CONFIG")

    try:
        server = NetOpsMCPHTTPServer(
            config_path=config_path,
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
