"""
Configuration models for the NetOps MCP server.

This module defines Pydantic models for configuration validation:
- Server settings
- Network diagnostic tools configuration
- Security settings
- Logging configuration
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class LoggingConfig(BaseModel):
    """Model for logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None


class SecurityConfig(BaseModel):
    """Model for security configuration."""
    allow_privileged_commands: bool = False
    allowed_hosts: list[str] = Field(default_factory=list)
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    require_auth: bool = False
    api_keys: list[str] = Field(default_factory=list)
    enable_cors: bool = False
    cors_origins: list[str] = Field(default_factory=list)


class NetworkConfig(BaseModel):
    """Model for network diagnostic tools configuration."""
    default_timeout: int = 30
    max_retries: int = 3
    ping_count: int = 4
    traceroute_max_hops: int = 30
    nmap_scan_timeout: int = 300


class Config(BaseModel):
    """Root configuration model."""
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    custom_settings: Dict[str, Any] = Field(default_factory=dict)
