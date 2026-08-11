"""
Rate limiting middleware for NetOps MCP server.

Provides in-memory rate limiting using a sliding window algorithm.
Supports per-API-key rate limiting and configurable limits per endpoint.
"""

import asyncio
import logging
import time
from typing import Awaitable, Callable, Dict, List, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from .metrics import metrics_collector

logger = logging.getLogger("netops-mcp.rate_limiter")


class RateLimiter:
    """
    In-memory sliding window rate limiter.

    Tracks requests per client (API key or IP) and enforces rate limits.
    """

    def __init__(
        self,
        requests_per_window: int = 100,
        window_seconds: int = 60,
        time_func: Callable[[], float] = time.time,
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_window: Maximum requests allowed in the time window
            window_seconds: Time window in seconds
            time_func: Clock callable returning the current time in seconds.
                Injectable so sliding-window expiry is testable without sleeping.
        """
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        # Plain dict, not defaultdict: reading an unknown client must not
        # resurrect an empty bucket that the eviction logic just dropped.
        self.requests: Dict[str, List[float]] = {}
        self._now = time_func
        self._lock = asyncio.Lock()
        self._last_prune = time_func()

        logger.info(
            f"Rate limiter initialized: {requests_per_window} requests per {window_seconds}s"
        )

    def _cleanup_old_requests(self, client_id: str, current_time: float) -> None:
        """
        Remove requests outside the current time window.

        Drops the client's bucket entirely once it empties, so a client that
        stops sending traffic leaves nothing behind.

        Args:
            client_id: Client identifier
            current_time: Current timestamp
        """
        cutoff_time = current_time - self.window_seconds
        recent = [
            req_time for req_time in self.requests.get(client_id, []) if req_time > cutoff_time
        ]
        if recent:
            self.requests[client_id] = recent
        else:
            self.requests.pop(client_id, None)

    def _prune_all(self, current_time: float) -> None:
        """
        Evict every client whose requests have all aged out of the window.

        Per-client cleanup only runs when that client is seen again, so a
        caller rotating identifiers (e.g. source IPs) would otherwise grow the
        map without bound — a memory-exhaustion vector. This sweep caps that
        growth. Clients with in-window timestamps keep them, so limits are
        unaffected.

        Args:
            current_time: Current timestamp
        """
        cutoff_time = current_time - self.window_seconds
        for client_id in list(self.requests):
            recent = [req_time for req_time in self.requests[client_id] if req_time > cutoff_time]
            if recent:
                self.requests[client_id] = recent
            else:
                del self.requests[client_id]

    async def is_allowed(self, client_id: str) -> Tuple[bool, int, int]:
        """
        Check if a request is allowed for the client.

        Args:
            client_id: Client identifier (API key hash or IP)

        Returns:
            Tuple of (allowed, remaining, reset_time)
            - allowed: Whether the request is allowed
            - remaining: Number of requests remaining in window
            - reset_time: Seconds until rate limit resets
        """
        async with self._lock:
            current_time = self._now()

            # Opportunistically evict stale buckets (at most once per window)
            # so rotating clients that never return cannot grow the map.
            if current_time - self._last_prune >= self.window_seconds:
                self._prune_all(current_time)
                self._last_prune = current_time

            # Clean up old requests
            self._cleanup_old_requests(client_id, current_time)

            # Count requests in current window
            bucket = self.requests.get(client_id, [])
            request_count = len(bucket)

            # Check if limit exceeded
            if request_count >= self.requests_per_window:
                oldest_request = min(bucket)
                reset_time = int(oldest_request + self.window_seconds - current_time)
                return False, 0, reset_time

            # Allow request and record it
            self.requests.setdefault(client_id, []).append(current_time)
            remaining = self.requests_per_window - request_count - 1

            return True, remaining, self.window_seconds

    async def get_stats(self, client_id: str) -> Dict[str, int]:
        """
        Get rate limit statistics for a client.

        Args:
            client_id: Client identifier

        Returns:
            Dictionary with rate limit stats
        """
        async with self._lock:
            current_time = self._now()
            self._cleanup_old_requests(client_id, current_time)

            request_count = len(self.requests.get(client_id, []))
            remaining = max(0, self.requests_per_window - request_count)

            return {
                "limit": self.requests_per_window,
                "remaining": remaining,
                "used": request_count,
                "window_seconds": self.window_seconds,
            }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting HTTP requests.

    Enforces rate limits per client (API key or IP address).
    Adds rate limit headers to responses.
    """

    def __init__(
        self,
        app: ASGIApp,
        requests_per_window: int = 100,
        window_seconds: int = 60,
        exempt_paths: Optional[set[str]] = None,
    ):
        """
        Initialize rate limit middleware.

        Args:
            app: ASGI application
            requests_per_window: Maximum requests per window
            window_seconds: Time window in seconds
            exempt_paths: Paths exempt from rate limiting
        """
        super().__init__(app)
        self.rate_limiter = RateLimiter(requests_per_window, window_seconds)
        self.exempt_paths = exempt_paths or {"/health", "/metrics"}

        logger.info("Rate limit middleware initialized")
        logger.info(f"Exempt paths: {self.exempt_paths}")

    def _get_client_identifier(self, request: Request) -> str:
        """
        Get unique identifier for the client.

        Uses API key hash if authenticated, otherwise IP address.

        Args:
            request: The incoming request

        Returns:
            Client identifier string
        """
        # If authenticated, use API key hash
        if hasattr(request.state, "api_key_hash"):
            return f"key:{request.state.api_key_hash}"

        # Otherwise use IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable]):
        """
        Process the request and enforce rate limiting.

        Args:
            request: The incoming request
            call_next: The next middleware/handler

        Returns:
            Response from next handler or rate limit error
        """
        # Check if path is exempt from rate limiting
        path = request.url.path
        if path in self.exempt_paths:
            logger.debug(f"Path {path} is exempt from rate limiting")
            response = await call_next(request)
            return response

        # Get client identifier
        client_id = self._get_client_identifier(request)

        # Check rate limit
        allowed, remaining, reset_time = await self.rate_limiter.is_allowed(client_id)

        if not allowed:
            # WR-05: record the throttle event so rate_limit_hits_total reflects
            # real abuse instead of being a permanently-zero exported counter.
            metrics_collector.record_rate_limit_hit()
            logger.warning(f"Rate limit exceeded for {client_id} on {path}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Please try again in {reset_time} seconds.",
                    "retry_after": reset_time,
                },
                headers={
                    "X-RateLimit-Limit": str(self.rate_limiter.requests_per_window),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + reset_time),
                    "Retry-After": str(reset_time),
                },
            )

        # Request allowed, process it
        logger.debug(f"Request allowed for {client_id}, remaining: {remaining}")
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.requests_per_window)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(
            int(time.time()) + self.rate_limiter.window_seconds
        )

        return response
