"""Shared MCP tool registry for NetOpsMCP (REF-04, REF-05).

Both the stdio server (``server.py``) and the HTTP server (``server_http.py``)
register the identical 26-tool MCP surface. Historically each duplicated a
~200-line ``_setup_tools`` body, which forced every tool-signature change to be
made in two places (CLAUDE.md architectural constraint). This module collapses
that duplication into a single :func:`register_tools` function.

The tool signatures use the ``Annotated`` + pydantic ``Field`` style copied
VERBATIM from ``server.py``. This style is load-bearing for the golden
schema snapshot: it is what gives the stdio schema its 56 property-level
descriptions. Registering the same signatures on the fastmcp 2.x (HTTP) class
enriches the HTTP schema so it differs from stdio by only the SDK-added schema
root ``title`` (already normalized away by the cross-server snapshot test).

``register_tools`` never constructs a FastMCP instance; it only decorates the
``mcp`` passed in, so it works with both the ``mcp.server.fastmcp.FastMCP``
(stdio) and standalone ``fastmcp.FastMCP`` (HTTP) classes. It returns the
dynamic tool count (REF-05) derived from the FastMCP instance rather than the
old hardcoded literal ``26``.
"""

import json
from typing import Annotated, Any, Optional

from mcp.types import TextContent as Content
from pydantic import Field

from ..utils.system_check import check_required_tools as check_tools_status
from ..utils.system_check import get_system_info


def _registered_tool_count(mcp: Any) -> int:
    """Best-effort count of tools registered on a FastMCP instance (REF-05, WR-03).

    REF-05 derives the tool count dynamically instead of hardcoding ``26``. Both
    the stdio SDK ``mcp.server.fastmcp.FastMCP`` and the standalone
    ``fastmcp.FastMCP`` expose that count only through the private
    ``_tool_manager._tools`` mapping at the pinned versions (mcp 1.13.0 /
    fastmcp 2.11.3). There is no SYNC public accessor that works uniformly across
    both — the SDK's ``_tool_manager.list_tools()`` is synchronous but fastmcp's
    is a coroutine, and this helper is called from synchronous code (registration
    return and the ``health`` tool).

    WR-03: the private access is therefore wrapped defensively. An upstream
    rename of ``_tool_manager`` or ``_tools`` (the ``mcp`` SDK tracks GitHub HEAD
    per CLAUDE.md) degrades this to a graceful ``0`` instead of raising
    ``AttributeError`` at registration return / inside the ``health`` tool. The
    focused guard test in ``tests/test_registry.py`` asserts the private path
    still exists on BOTH FastMCP classes, so an SDK bump fails LOUDLY in CI
    rather than silently reporting a zero tool count at runtime.
    """
    tool_mgr = getattr(mcp, "_tool_manager", None)
    tools = getattr(tool_mgr, "_tools", None)
    try:
        return len(tools) if tools is not None else 0
    except TypeError:
        return 0


def register_tools(mcp: Any, tools: Any) -> int:
    """Register all 26 MCP tools on ``mcp``.

    Args:
        mcp: A FastMCP instance (either the stdio ``mcp.server.fastmcp.FastMCP``
            or the HTTP standalone ``fastmcp.FastMCP``). Only its ``@mcp.tool``
            decorator surface is used; it is never constructed here.
        tools: The server instance exposing the tool-group attributes
            (``http_tools``, ``connectivity_tools``, ``dns_tools``,
            ``discovery_tools``, ``network_tools``, ``monitoring_tools``,
            ``scanning_tools``) plus per-server state (e.g. ``_tests_passed``).

    Returns:
        The dynamic tool count from the FastMCP instance (REF-05). This is the
        single source of truth for the tool count; callers store it (e.g. as
        ``self.tool_count``) instead of hardcoding ``26``.
    """

    # HTTP/API Testing Tools
    @mcp.tool(description="Execute HTTP request using curl")
    def curl_request(
        url: Annotated[str, Field(description="Target URL")],
        method: Annotated[str, Field(description="HTTP method", default="GET")] = "GET",
        headers: Annotated[Optional[dict], Field(description="HTTP headers")] = None,
        data: Annotated[Optional[str], Field(description="Request body")] = None,
        timeout: Annotated[int, Field(description="Timeout in seconds", default=30)] = 30
    ):
        return tools.http_tools.curl_request(url, method, headers, data, timeout)

    @mcp.tool(description="Execute HTTP request using httpie")
    def httpie_request(
        url: Annotated[str, Field(description="Target URL")],
        method: Annotated[str, Field(description="HTTP method", default="GET")] = "GET",
        headers: Annotated[Optional[dict], Field(description="HTTP headers")] = None,
        data: Annotated[Optional[dict], Field(description="Request data")] = None,
        timeout: Annotated[int, Field(description="Timeout in seconds", default=30)] = 30
    ):
        return tools.http_tools.httpie_request(url, method, headers, data, timeout)

    @mcp.tool(description="Test API endpoint with validation")
    def api_test(
        url: Annotated[str, Field(description="API endpoint URL")],
        method: Annotated[str, Field(description="HTTP method", default="GET")] = "GET",
        expected_status: Annotated[int, Field(description="Expected HTTP status", default=200)] = 200,
        headers: Annotated[Optional[dict], Field(description="HTTP headers")] = None,
        timeout: Annotated[int, Field(description="Timeout in seconds", default=30)] = 30
    ):
        return tools.http_tools.api_test(url, method, expected_status, headers, timeout)

    # Network Connectivity Tools
    @mcp.tool(description="Ping a host to test connectivity")
    def ping_host(
        host: Annotated[str, Field(description="Target host")],
        count: Annotated[int, Field(description="Number of ping packets", default=4)] = 4,
        timeout: Annotated[int, Field(description="Timeout in seconds", default=10)] = 10
    ):
        return tools.connectivity_tools.ping_host(host, count, timeout)

    @mcp.tool(description="Perform traceroute to a target")
    def traceroute_path(
        target: Annotated[str, Field(description="Target host")],
        max_hops: Annotated[int, Field(description="Maximum number of hops", default=30)] = 30,
        timeout: Annotated[int, Field(description="Timeout in seconds", default=30)] = 30
    ):
        return tools.connectivity_tools.traceroute_path(target, max_hops, timeout)

    @mcp.tool(description="Monitor network path using mtr")
    def mtr_monitor(
        target: Annotated[str, Field(description="Target host")],
        count: Annotated[int, Field(description="Number of probes", default=10)] = 10,
        timeout: Annotated[int, Field(description="Timeout in seconds", default=30)] = 30
    ):
        return tools.connectivity_tools.mtr_monitor(target, count, timeout)

    @mcp.tool(description="Test port connectivity using telnet")
    def telnet_connect(
        host: Annotated[str, Field(description="Target host")],
        port: Annotated[int, Field(description="Target port")],
        timeout: Annotated[int, Field(description="Timeout in seconds", default=10)] = 10
    ):
        return tools.connectivity_tools.telnet_connect(host, port, timeout)

    @mcp.tool(description="Test port connectivity using netcat")
    def netcat_test(
        host: Annotated[str, Field(description="Target host")],
        port: Annotated[int, Field(description="Target port")],
        timeout: Annotated[int, Field(description="Timeout in seconds", default=10)] = 10
    ):
        return tools.connectivity_tools.netcat_test(host, port, timeout)

    # DNS Tools
    @mcp.tool(description="Perform DNS lookup using nslookup")
    def nslookup_query(
        domain: Annotated[str, Field(description="Domain to lookup")],
        record_type: Annotated[str, Field(description="DNS record type", default="A")] = "A",
        server: Annotated[Optional[str], Field(description="DNS server")] = None
    ):
        return tools.dns_tools.nslookup_query(domain, record_type, server)

    @mcp.tool(description="Perform DNS lookup using dig")
    def dig_query(
        domain: Annotated[str, Field(description="Domain to lookup")],
        record_type: Annotated[str, Field(description="DNS record type", default="A")] = "A",
        server: Annotated[Optional[str], Field(description="DNS server")] = None
    ):
        return tools.dns_tools.dig_query(domain, record_type, server)

    @mcp.tool(description="Perform DNS lookup using host")
    def host_lookup(
        domain: Annotated[str, Field(description="Domain to lookup")],
        record_type: Annotated[str, Field(description="DNS record type", default="A")] = "A"
    ):
        return tools.dns_tools.host_lookup(domain, record_type)

    # Network Discovery Tools
    @mcp.tool(description="Scan network using nmap")
    def nmap_scan(
        target: Annotated[str, Field(description="Target host or network")],
        ports: Annotated[Optional[str], Field(description="Port range (e.g., '22,80,443')")] = None,
        scan_type: Annotated[str, Field(description="Scan type", default="basic")] = "basic",
        timeout: Annotated[int, Field(description="Timeout in seconds", default=300)] = 300
    ):
        return tools.discovery_tools.nmap_scan(target, ports, scan_type, timeout)

    @mcp.tool(description="Discover network services")
    def service_discovery(
        target: Annotated[str, Field(description="Target host")],
        ports: Annotated[Optional[str], Field(description="Port range")] = None
    ):
        return tools.discovery_tools.service_discovery(target, ports)

    # System Network Tools
    @mcp.tool(description="Show network connections using ss")
    def ss_connections(
        state: Annotated[Optional[str], Field(description="Connection state")] = None,
        protocol: Annotated[Optional[str], Field(description="Protocol (tcp/udp)")] = None
    ):
        return tools.network_tools.ss_connections(state, protocol)

    @mcp.tool(description="Show network connections using netstat")
    def netstat_connections(
        state: Annotated[Optional[str], Field(description="Connection state")] = None,
        protocol: Annotated[Optional[str], Field(description="Protocol (tcp/udp)")] = None
    ):
        return tools.network_tools.netstat_connections(state, protocol)

    @mcp.tool(description="Show ARP table")
    def arp_table():
        return tools.network_tools.arp_table()

    @mcp.tool(description="ARP ping a host")
    def arping_host(
        host: Annotated[str, Field(description="Target host")],
        count: Annotated[int, Field(description="Number of packets", default=4)] = 4
    ):
        return tools.network_tools.arping_host(host, count)

    # System Monitoring Tools
    @mcp.tool(description="Get system status")
    def system_status():
        return tools.monitoring_tools.system_status()

    @mcp.tool(description="Get CPU usage information")
    def cpu_usage():
        return tools.monitoring_tools.cpu_usage()

    @mcp.tool(description="Get memory usage information")
    def memory_usage():
        return tools.monitoring_tools.memory_usage()

    @mcp.tool(description="Get disk usage information")
    def disk_usage():
        return tools.monitoring_tools.disk_usage()

    @mcp.tool(description="List running processes")
    def process_list(
        limit: Annotated[int, Field(description="Number of processes to show", default=20)] = 20
    ):
        return tools.monitoring_tools.process_list(limit)

    # Security Tools
    @mcp.tool(description="Scan ports on a target")
    def port_scan(
        target: Annotated[str, Field(description="Target host")],
        ports: Annotated[str, Field(description="Port range (e.g., '1-1000')")],
        timeout: Annotated[int, Field(description="Timeout in seconds", default=60)] = 60
    ):
        return tools.scanning_tools.port_scan(target, ports, timeout)

    @mcp.tool(description="Enumerate services on a target")
    def service_enumeration(
        target: Annotated[str, Field(description="Target host")],
        ports: Annotated[Optional[str], Field(description="Port range")] = None
    ):
        return tools.scanning_tools.service_enumeration(target, ports)

    # System Tools
    @mcp.tool(description="Check required system tools")
    def check_required_tools():
        # Unified body: typed Content envelope (server.py style), with the
        # HTTP server's defensive try/except so a system-check failure returns
        # a structured error instead of propagating.
        try:
            tool_status = check_tools_status()
            system_info = get_system_info()

            response_data = {
                "tools": tool_status,
                "system_info": system_info,
                "missing_tools": tool_status["missing_tools"],
            }

            return [Content(type="text", text=json.dumps(response_data, indent=2))]
        except Exception as e:
            return [Content(type="text", text=json.dumps({"error": str(e)}, indent=2))]

    @mcp.tool(description="Health check endpoint")
    def health():
        # Unified body: reports the DYNAMIC tool count (REF-05) plus startup
        # test status. `_tests_passed` is stdio-only state (None on the HTTP
        # server, which never runs startup tests) — acceptable per plan.
        tests_passed = getattr(tools, "_tests_passed", None)
        status = (
            "ok" if tests_passed is True
            else ("degraded" if tests_passed is False else "unknown")
        )
        return [Content(type="text", text=json.dumps({
            "status": status,
            "tests_passed": tests_passed,
            "mcp_tools": _registered_tool_count(mcp),
            "details": (
                "Startup tests passed" if tests_passed is True
                else ("Startup tests failed" if tests_passed is False
                      else "No tests executed")
            )
        }))]

    # REF-05: derive the count dynamically from the FastMCP instance rather
    # than the old hardcoded literal 26. WR-03: access is wrapped defensively
    # (see _registered_tool_count) so an SDK internals rename degrades to 0
    # instead of crashing server construction; the CI guard test catches it.
    return _registered_tool_count(mcp)
