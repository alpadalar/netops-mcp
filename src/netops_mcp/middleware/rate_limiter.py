"""
Rate limiting middleware for NetOps MCP server.

Provides in-memory rate limiting using a sliding window algorithm.
Supports per-API-key rate limiting and configurable limits per endpoint.
"""

import time
import logging
from typing import Dict, Tuple, Optional, Callable, Awaitable
from collections import defaultdict
from threading import Lock
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

logger = logging.getLogger("netops-mcp.rate_limiter")


class RateLimiter:
    """
    In-memory sliding window rate limiter.
    
    Tracks requests per client (API key or IP) and enforces rate limits.
    """
    
    def __init__(self, requests_per_window: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_window: Maximum requests allowed in the time window
            window_seconds: Time window in seconds
        """
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.requests: Dict[str, list[float]] = defaultdict(list)
        self.lock = Lock()
        
        logger.info(f"Rate limiter initialized: {requests_per_window} requests per {window_seconds}s")
    
    def _cleanup_old_requests(self, client_id: str, current_time: float) -> None:
        """
        Remove requests outside the current time window.
        
        Args:
            client_id: Client identifier
            current_time: Current timestamp
        """
        cutoff_time = current_time - self.window_seconds
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff_time
        ]
    
    def is_allowed(self, client_id: str) -> Tuple[bool, int, int]:
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
        with self.lock:
            current_time = time.time()
            
            # Clean up old requests
            self._cleanup_old_requests(client_id, current_time)
            
            # Count requests in current window
            request_count = len(self.requests[client_id])
            
            # Check if limit exceeded
            if request_count >= self.requests_per_window:
                oldest_request = min(self.requests[client_id])
                reset_time = int(oldest_request + self.window_seconds - current_time)
                return False, 0, reset_time
            
            # Allow request and record it
            self.requests[client_id].append(current_time)
            remaining = self.requests_per_window - request_count - 1
            
            return True, remaining, self.window_seconds
    
    def get_stats(self, client_id: str) -> Dict[str, int]:
        """
        Get rate limit statistics for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Dictionary with rate limit stats
        """
        with self.lock:
            current_time = time.time()
            self._cleanup_old_requests(client_id, current_time)
            
            request_count = len(self.requests[client_id])
            remaining = max(0, self.requests_per_window - request_count)
            
            return {
                "limit": self.requests_per_window,
                "remaining": remaining,
                "used": request_count,
                "window_seconds": self.window_seconds
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
        exempt_paths: Optional[set[str]] = None
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
        
        logger.info(f"Rate limit middleware initialized")
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
    
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable]
    ):
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
        allowed, remaining, reset_time = self.rate_limiter.is_allowed(client_id)
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for {client_id} on {path}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Please try again in {reset_time} seconds.",
                    "retry_after": reset_time
                },
                headers={
                    "X-RateLimit-Limit": str(self.rate_limiter.requests_per_window),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + reset_time),
                    "Retry-After": str(reset_time)
                }
            )
        
        # Request allowed, process it
        logger.debug(f"Request allowed for {client_id}, remaining: {remaining}")
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.requests_per_window)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.rate_limiter.window_seconds)
        
        return response


