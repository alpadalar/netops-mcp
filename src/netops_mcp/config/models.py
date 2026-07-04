"""
Configuration models for the NetOps MCP server.

This module defines Pydantic models for configuration validation:
- Server settings
- Network diagnostic tools configuration
- Security settings
- Logging configuration

All models are strict (`extra='forbid'`): unknown keys fail loudly at load
time instead of being silently dropped.
"""

import re
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LoggingConfig(BaseModel):
    """Model for logging configuration."""
    model_config = ConfigDict(extra='forbid')

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None


class SecurityConfig(BaseModel):
    """Model for security configuration."""
    model_config = ConfigDict(extra='forbid')

    allow_privileged_commands: bool = False
    allowed_hosts: list[str] = Field(default_factory=list)
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    require_auth: bool = True
    api_keys: list[str] = Field(default_factory=list)
    enable_cors: bool = False
    cors_origins: list[str] = Field(default_factory=list)
    cors_allow_credentials: bool = False

    @field_validator("api_keys")
    @classmethod
    def _keys_must_be_hashed(cls, v: list[str]) -> list[str]:
        """Reject api_keys entries that are not 'sha256:<64-hex>' digests."""
        for k in v:
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", k):
                raise ValueError(
                    "api_keys entries must be 'sha256:<64-hex>' digests. Hash your key: "
                    "python -c \"import hashlib;"
                    "print('sha256:'+hashlib.sha256(b'YOUR-KEY').hexdigest())\""
                )
        return v

    @model_validator(mode='after')
    def _no_wildcard_with_credentials(self) -> "SecurityConfig":
        """Reject wildcard CORS origins combined with credentials.

        Starlette's CORSMiddleware reflects arbitrary request origins when
        configured with allow_origins=['*'] and allow_credentials=True,
        exposing credentialed responses cross-site. The combination is made
        unrepresentable at config load time.
        """
        if self.cors_allow_credentials and any("*" in o for o in self.cors_origins):
            raise ValueError(
                "cors_origins may not contain wildcards when cors_allow_credentials is true"
            )
        return self


class NetworkConfig(BaseModel):
    """Model for network diagnostic tools configuration."""
    model_config = ConfigDict(extra='forbid')

    default_timeout: int = 30
    max_retries: int = 3
    ping_count: int = 4
    traceroute_max_hops: int = 30
    nmap_scan_timeout: int = 300
    max_scan_timeout: int = 300
    allowed_ports: str = "1-65535"


class ServerConfig(BaseModel):
    """Model for HTTP server configuration (host/port/path defaults)."""
    model_config = ConfigDict(extra='forbid')

    host: str = "0.0.0.0"
    port: int = 8815
    path: str = "/netops-mcp"


class Config(BaseModel):
    """Root configuration model."""
    model_config = ConfigDict(extra='forbid')

    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    custom_settings: Dict[str, Any] = Field(default_factory=dict)
