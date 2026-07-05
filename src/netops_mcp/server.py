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
import os
import sys
import signal
from typing import Optional, List

from mcp.server.fastmcp import FastMCP

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

        # Initialize tools (thread config so tools can read self._security)
        self.http_tools = HTTPTools(self.config)
        self.connectivity_tools = ConnectivityTools(self.config)
        self.dns_tools = DNSTools(self.config)
        self.discovery_tools = DiscoveryTools(self.config)
        self.network_tools = NetworkTools(self.config)
        self.monitoring_tools = MonitoringTools(self.config)
        self.scanning_tools = ScanningTools(self.config)

        # Initialize MCP server
        self.mcp = FastMCP("NetOpsMCP")
        self._tests_passed: Optional[bool] = None
        # Register the shared 26-tool surface (REF-04). tool_count is derived
        # dynamically from the FastMCP instance (REF-05), not hardcoded.
        self.tool_count = register_tools(self.mcp, self)

    def _test_system_requirements(self) -> None:
        """Test system requirements and required tools."""
        try:
            self.logger.info("Testing system requirements...")

            # Check required tools
            tool_status = check_tools_status()
            missing_tools = tool_status['missing_tools']

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
                # WR-01: stdin=DEVNULL — without it the pytest child (and the
                # entire test process tree it spawns) inherits fd 0, which at
                # this point is already the client's MCP JSON-RPC pipe.
                result = subprocess.run(
                    [sys.executable, "-m", "pytest", "-q"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    env=env,
                )
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
        for tool in tools['available_tools']:
            print(f"  ✅ {tool}")
        for tool in tools['missing_tools']:
            print(f"  ❌ {tool}")

        missing = tools['missing_tools']
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
