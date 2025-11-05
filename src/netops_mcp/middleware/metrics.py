"""
Prometheus metrics middleware for NetOps MCP server.

Provides metrics collection and export for monitoring:
- HTTP request metrics (count, duration, status codes)
- Rate limit metrics
- Authentication metrics
- Tool execution metrics
"""

import time
import logging
from typing import Dict, Callable, Awaitable
from collections import defaultdict
from threading import Lock
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse
from starlette.types import ASGIApp

logger = logging.getLogger("netops-mcp.metrics")


class MetricsCollector:
    """
    Collect and store metrics for Prometheus export.
    
    Thread-safe metrics collection for HTTP requests and application events.
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self.lock = Lock()
        
        # HTTP metrics
        self.http_requests_total: Dict[tuple, int] = defaultdict(int)
        self.http_request_duration_seconds: Dict[tuple, list] = defaultdict(list)
        self.http_requests_in_progress = 0
        
        # Authentication metrics
        self.auth_attempts_total = 0
        self.auth_failures_total = 0
        
        # Rate limit metrics
        self.rate_limit_hits_total = 0
        
        # Tool execution metrics
        self.tool_executions_total: Dict[str, int] = defaultdict(int)
        self.tool_execution_duration: Dict[str, list] = defaultdict(list)
        self.tool_failures_total: Dict[str, int] = defaultdict(int)
    
    def record_http_request(self, method: str, path: str, status_code: int, duration: float):
        """
        Record an HTTP request.
        
        Args:
            method: HTTP method
            path: Request path
            status_code: Response status code
            duration: Request duration in seconds
        """
        with self.lock:
            key = (method, path, status_code)
            self.http_requests_total[key] += 1
            self.http_request_duration_seconds[key].append(duration)
    
    def inc_requests_in_progress(self):
        """Increment in-progress requests counter."""
        with self.lock:
            self.http_requests_in_progress += 1
    
    def dec_requests_in_progress(self):
        """Decrement in-progress requests counter."""
        with self.lock:
            self.http_requests_in_progress = max(0, self.http_requests_in_progress - 1)
    
    def record_auth_attempt(self, success: bool):
        """Record an authentication attempt."""
        with self.lock:
            self.auth_attempts_total += 1
            if not success:
                self.auth_failures_total += 1
    
    def record_rate_limit_hit(self):
        """Record a rate limit hit."""
        with self.lock:
            self.rate_limit_hits_total += 1
    
    def record_tool_execution(self, tool_name: str, duration: float, success: bool):
        """
        Record a tool execution.
        
        Args:
            tool_name: Name of the tool
            duration: Execution duration in seconds
            success: Whether execution was successful
        """
        with self.lock:
            self.tool_executions_total[tool_name] += 1
            self.tool_execution_duration[tool_name].append(duration)
            if not success:
                self.tool_failures_total[tool_name] += 1
    
    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus text format.
        
        Returns:
            Prometheus-formatted metrics string
        """
        lines = []
        
        with self.lock:
            # HTTP request metrics
            lines.append("# HELP http_requests_total Total number of HTTP requests")
            lines.append("# TYPE http_requests_total counter")
            for (method, path, status), count in self.http_requests_total.items():
                lines.append(
                    f'http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
                )
            
            # HTTP request duration
            lines.append("# HELP http_request_duration_seconds HTTP request duration in seconds")
            lines.append("# TYPE http_request_duration_seconds histogram")
            for (method, path, status), durations in self.http_request_duration_seconds.items():
                if durations:
                    count = len(durations)
                    total = sum(durations)
                    lines.append(
                        f'http_request_duration_seconds_sum{{method="{method}",path="{path}",status="{status}"}} {total:.6f}'
                    )
                    lines.append(
                        f'http_request_duration_seconds_count{{method="{method}",path="{path}",status="{status}"}} {count}'
                    )
            
            # Requests in progress
            lines.append("# HELP http_requests_in_progress Number of HTTP requests currently being processed")
            lines.append("# TYPE http_requests_in_progress gauge")
            lines.append(f"http_requests_in_progress {self.http_requests_in_progress}")
            
            # Authentication metrics
            lines.append("# HELP auth_attempts_total Total number of authentication attempts")
            lines.append("# TYPE auth_attempts_total counter")
            lines.append(f"auth_attempts_total {self.auth_attempts_total}")
            
            lines.append("# HELP auth_failures_total Total number of authentication failures")
            lines.append("# TYPE auth_failures_total counter")
            lines.append(f"auth_failures_total {self.auth_failures_total}")
            
            # Rate limit metrics
            lines.append("# HELP rate_limit_hits_total Total number of rate limit hits")
            lines.append("# TYPE rate_limit_hits_total counter")
            lines.append(f"rate_limit_hits_total {self.rate_limit_hits_total}")
            
            # Tool execution metrics
            lines.append("# HELP tool_executions_total Total number of tool executions")
            lines.append("# TYPE tool_executions_total counter")
            for tool_name, count in self.tool_executions_total.items():
                lines.append(f'tool_executions_total{{tool="{tool_name}"}} {count}')
            
            lines.append("# HELP tool_execution_duration_seconds Tool execution duration in seconds")
            lines.append("# TYPE tool_execution_duration_seconds histogram")
            for tool_name, durations in self.tool_execution_duration.items():
                if durations:
                    count = len(durations)
                    total = sum(durations)
                    lines.append(f'tool_execution_duration_seconds_sum{{tool="{tool_name}"}} {total:.6f}')
                    lines.append(f'tool_execution_duration_seconds_count{{tool="{tool_name}"}} {count}')
            
            lines.append("# HELP tool_failures_total Total number of tool execution failures")
            lines.append("# TYPE tool_failures_total counter")
            for tool_name, count in self.tool_failures_total.items():
                lines.append(f'tool_failures_total{{tool="{tool_name}"}} {count}')
        
        return "\n".join(lines) + "\n"


# Global metrics collector instance
metrics_collector = MetricsCollector()


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting HTTP request metrics.
    
    Tracks request counts, durations, and status codes.
    """
    
    def __init__(self, app: ASGIApp, collector: MetricsCollector = None):
        """
        Initialize metrics middleware.
        
        Args:
            app: ASGI application
            collector: MetricsCollector instance (uses global if not provided)
        """
        super().__init__(app)
        self.collector = collector or metrics_collector
    
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable]
    ):
        """
        Process request and collect metrics.
        
        Args:
            request: The incoming request
            call_next: The next middleware/handler
            
        Returns:
            Response from next handler
        """
        # Skip metrics for /metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Record request start
        start_time = time.time()
        self.collector.inc_requests_in_progress()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Record metrics
            duration = time.time() - start_time
            self.collector.record_http_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration
            )
            
            return response
        
        finally:
            self.collector.dec_requests_in_progress()


def create_metrics_endpoint(collector: MetricsCollector = None) -> Callable:
    """
    Create a metrics endpoint handler.
    
    Args:
        collector: MetricsCollector instance (uses global if not provided)
        
    Returns:
        Async function that returns Prometheus metrics
    """
    collector = collector or metrics_collector
    
    async def metrics_endpoint(request: Request) -> Response:
        """Metrics endpoint handler."""
        metrics_text = collector.export_prometheus()
        return PlainTextResponse(
            metrics_text,
            headers={"Content-Type": "text/plain; version=0.0.4"}
        )
    
    return metrics_endpoint






