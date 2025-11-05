"""
Authentication middleware for NetOps MCP server.

Provides API key-based authentication using Bearer tokens or API-Key headers.
Supports multiple API keys for different clients and allows certain endpoints
to be accessible without authentication (e.g., health checks).
"""

import hashlib
import secrets
import logging
from typing import Optional, List, Set, Callable, Awaitable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

logger = logging.getLogger("netops-mcp.auth")


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication.
    
    Supports:
    - Bearer token in Authorization header
    - API-Key in custom header
    - Exempt paths (health checks, etc.)
    - Multiple API keys
    """
    
    def __init__(
        self,
        app: ASGIApp,
        api_keys: List[str],
        require_auth: bool = True,
        exempt_paths: Optional[Set[str]] = None
    ):
        """
        Initialize authentication middleware.
        
        Args:
            app: ASGI application
            api_keys: List of valid API keys (hashed or plain)
            require_auth: Whether authentication is required
            exempt_paths: Set of paths that don't require authentication
        """
        super().__init__(app)
        self.api_keys = api_keys
        self.require_auth = require_auth
        self.exempt_paths = exempt_paths or {"/health", "/metrics"}
        
        # Hash API keys for secure comparison
        self.hashed_keys = {self._hash_key(key) for key in api_keys}
        
        logger.info(f"Authentication middleware initialized with {len(api_keys)} keys")
        logger.info(f"Exempt paths: {self.exempt_paths}")
        logger.info(f"Authentication required: {require_auth}")
    
    @staticmethod
    def _hash_key(key: str) -> str:
        """Hash an API key using SHA-256."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def _extract_api_key(self, request: Request) -> Optional[str]:
        """
        Extract API key from request headers.
        
        Supports:
        - Authorization: Bearer <token>
        - X-API-Key: <token>
        - API-Key: <token>
        
        Returns:
            API key if found, None otherwise
        """
        # Try Authorization header with Bearer token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix
        
        # Try X-API-Key header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return api_key
        
        # Try API-Key header (alternative)
        api_key = request.headers.get("API-Key")
        if api_key:
            return api_key
        
        return None
    
    def _validate_api_key(self, api_key: str) -> bool:
        """
        Validate an API key against stored keys.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check if the key matches any stored key (plain or hashed)
        if api_key in self.api_keys:
            return True
        
        # Check hashed version
        hashed = self._hash_key(api_key)
        return hashed in self.hashed_keys
    
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable]
    ):
        """
        Process the request and validate authentication.
        
        Args:
            request: The incoming request
            call_next: The next middleware/handler
            
        Returns:
            Response from next handler or authentication error
        """
        # Check if path is exempt from authentication
        path = request.url.path
        if path in self.exempt_paths:
            logger.debug(f"Path {path} is exempt from authentication")
            return await call_next(request)
        
        # If authentication is not required, allow all requests
        if not self.require_auth:
            logger.debug("Authentication not required, allowing request")
            return await call_next(request)
        
        # Extract API key from request
        api_key = self._extract_api_key(request)
        
        if not api_key:
            logger.warning(f"No API key provided for {path}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Authentication required",
                    "message": "Please provide an API key using Authorization header (Bearer token) or X-API-Key header"
                },
                headers={
                    "WWW-Authenticate": 'Bearer realm="NetOpsMCP"'
                }
            )
        
        # Validate API key
        if not self._validate_api_key(api_key):
            logger.warning(f"Invalid API key attempt for {path}")
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Invalid API key",
                    "message": "The provided API key is not valid"
                }
            )
        
        # API key is valid, proceed with request
        logger.debug(f"Valid API key provided for {path}")
        
        # Add authentication info to request state
        request.state.authenticated = True
        request.state.api_key_hash = self._hash_key(api_key)[:8]  # Store partial hash for logging
        
        return await call_next(request)


def generate_api_key(length: int = 32) -> str:
    """
    Generate a secure random API key.
    
    Args:
        length: Length of the API key (default: 32)
        
    Returns:
        Secure random API key
    """
    return secrets.token_urlsafe(length)


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage.
    
    Args:
        api_key: The API key to hash
        
    Returns:
        SHA-256 hash of the API key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


