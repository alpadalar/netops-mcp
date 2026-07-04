"""
HTTP-based MCP server implementation for NetOpsMCP.

This module provides an HTTP transport layer for the MCP server,
supporting both regular HTTP and streamable HTTP transports.
"""

import hashlib
import logging
import os
import secrets
import signal
import sys
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

from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse

from .config.loader import load_config
from .core.logging import setup_logging
from .middleware.auth import AuthenticationMiddleware
from .middleware.metrics import MetricsMiddleware, create_metrics_endpoint
from .middleware.rate_limiter import RateLimitMiddleware
from .tools.network.connectivity_tools import ConnectivityTools
from .tools.network.discovery_tools import DiscoveryTools
from .tools.network.dns_tools import DNSTools
from .tools.network.http_tools import HTTPTools
from .tools.registry import register_tools
from .tools.security.scanning_tools import ScanningTools
from .tools.system.monitoring_tools import MonitoringTools
from .tools.system.network_tools import NetworkTools
from .utils.system_check import check_required_tools as check_tools_status

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

        # Register the shared 26-tool surface (REF-04). tool_count is derived
        # dynamically from the FastMCP instance (REF-05), replacing the former
        # hardcoded 26 in the tool-registration path.
        self.tool_count = register_tools(self.mcp, self)

        # PERF-03: cache system-tool availability ONCE at startup instead of
        # forking ~15 subprocess probes every 30s from a background thread. The
        # /health route reads this cache; no per-hit fork storm.
        self._tool_status_cache = check_tools_status()

        # REF-07: register /health and /metrics on the FastMCP instance BEFORE
        # any build_http_app() call, so custom_route bakes them into the
        # ACTUALLY served app (via mcp._additional_http_routes) rather than the
        # throwaway app the old (now-removed) health wiring configured.
        self._register_http_routes()

    def _register_http_routes(self) -> None:
        """Register /health and /metrics on the REAL served app (REF-07).

        ``custom_route`` appends to ``mcp._additional_http_routes``, which
        FastMCP's ``create_streamable_http_app`` bakes into whichever Starlette
        app :meth:`build_http_app` constructs. That is what makes these routes —
        and the middleware stack — live on the ACTUALLY served app instead of the
        throwaway ``http_app()`` the old (now-removed) health wiring configured.
        Must run in ``__init__`` before any :meth:`build_http_app` call.
        """
        metrics_handler = create_metrics_endpoint()

        @self.mcp.custom_route("/health", methods=["GET"])
        async def health(request):
            """Liveness/readiness endpoint backed by the startup tool cache.

            Reads the PERF-03 startup cache (no per-hit subprocess fork) and
            reports the dynamic MCP tool count (REF-05). Exempt from auth and
            rate limiting so container/orchestrator probes always succeed —
            this is the route the Docker/compose healthcheck curls at ROOT.
            """
            cache = self._tool_status_cache
            available = len(cache["available_tools"])
            total = available + len(cache["missing_tools"])
            return JSONResponse({
                "status": "healthy",
                "server": "NetOpsMCP-HTTP",
                "mcp_tools": self.tool_count,
                "system_tools_available": available,
                "system_tools_total": total,
                "authentication": self.config.security.require_auth,
            })

        @self.mcp.custom_route("/metrics", methods=["GET"])
        async def metrics(request):
            """Prometheus metrics endpoint delegating to the global collector."""
            return await metrics_handler(request)

    def build_http_app(self):
        """Build the ACTUALLY-served Starlette app with the middleware stack (REF-07).

        The single served app is constructed via
        ``FastMCP.http_app(path=, middleware=[...])`` so the auth, rate-limit,
        CORS, metrics and trusted-host middleware attach to the app uvicorn
        serves — closing the Phase 2 CR-01 throwaway-app bypass. The /health and
        /metrics routes registered by :meth:`_register_http_routes` are baked in
        by FastMCP from ``mcp._additional_http_routes``.

        Middleware ordering trap (RESEARCH Pitfall 3): ``add_middleware`` is
        LIFO/prepend (last added = outermost), but a ``Middleware([...])`` list
        is applied first=outermost. The list is therefore built in
        outermost->inner order ``[TrustedHost, Auth, RateLimit, CORS, Metrics]``
        to preserve the request flow the former ``_add_middleware`` produced.
        """
        security = self.config.security
        middleware = []

        if security.allowed_hosts:
            middleware.append(
                Middleware(TrustedHostMiddleware, allowed_hosts=security.allowed_hosts)
            )

        if security.require_auth:
            # WR-01: fail-safe seam. The auth-enforcement invariant lives HERE,
            # on the served app itself — not only in run()'s startup gate. Any
            # caller that builds and serves this app (e.g. the E2E harness, which
            # bypasses run()) is guaranteed to either serve WITH auth attached or
            # fail loudly at build time, never fail-open with require_auth=True
            # and no keys. Keeps the Phase 2 fail-fast style.
            if not security.api_keys:
                raise RuntimeError(
                    "require_auth is enabled but no api_keys are configured; "
                    "refusing to build an unauthenticated app. Configure "
                    "security.api_keys or explicitly set require_auth=false."
                )
            middleware.append(
                Middleware(
                    AuthenticationMiddleware,
                    api_keys=security.api_keys,
                    require_auth=True,
                    # WR-02: /metrics is NOT auth-exempt. The default bind is
                    # 0.0.0.0, so an unauthenticated Prometheus dump would
                    # disclose request paths/status/per-label counts to any
                    # origin that can reach the port. Only /health stays public
                    # (container/orchestrator liveness probes). Scrapers must
                    # send the API key; /metrics remains rate-limit-exempt below
                    # so authenticated scraping is never throttled.
                    exempt_paths={"/health"},
                )
            )

        middleware.append(
            Middleware(
                RateLimitMiddleware,
                requests_per_window=security.rate_limit_requests,
                window_seconds=security.rate_limit_window,
                exempt_paths={"/health", "/metrics"},
            )
        )

        if security.enable_cors:
            middleware.append(
                Middleware(
                    CORSMiddleware,
                    allow_origins=security.cors_origins,
                    allow_credentials=security.cors_allow_credentials,
                    allow_methods=["*"],
                    allow_headers=["*"],
                )
            )

        middleware.append(Middleware(MetricsMiddleware))

        return self.mcp.http_app(path=self.path, middleware=middleware)

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

            # REF-07: build the ONE served app (middleware + /health + /metrics
            # baked in) and drive uvicorn on it directly. Driving uvicorn here
            # (instead of FastMCP's own runner) lets the E2E harness serve the
            # exact same build_http_app() output — the strongest anti-throwaway
            # design; the harness proves this wiring at runtime.
            app = self.build_http_app()

            import uvicorn

            uvicorn.Server(
                uvicorn.Config(
                    app,
                    host=self.host,
                    port=self.port,
                    log_level="info",
                    lifespan="on",
                )
            ).run()
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
