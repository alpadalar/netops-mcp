"""
Configuration loading utilities for the NetOps MCP server.

This module handles loading and validation of server configuration:
- JSON configuration file loading
- Environment variable handling (including a .env file)
- Configuration validation using Pydantic models
- Error handling for invalid configurations
"""

import json
import os
from typing import Any, Dict, Optional

from .models import Config

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is a declared dependency, but stay graceful
    load_dotenv = None


def _parse_bool(value: str) -> bool:
    """Parse a boolean from an environment-variable string."""
    return value.strip().lower() in ("1", "true", "yes", "on")


def _parse_list(value: str) -> list:
    """Parse a comma-separated list, dropping empty entries."""
    return [item.strip() for item in value.split(",") if item.strip()]


def _apply_env_overrides(data: Dict[str, Any]) -> Dict[str, Any]:
    """Overlay environment variables onto a config dict (env takes precedence).

    Only variables that are actually set are applied, so file/defaults remain
    for everything else. Mirrors the names documented in env.production.example.
    """
    logging_cfg = data.setdefault("logging", {})
    security_cfg = data.setdefault("security", {})
    network_cfg = data.setdefault("network", {})

    # Logging
    if "LOG_LEVEL" in os.environ:
        logging_cfg["level"] = os.environ["LOG_LEVEL"]
    if "LOG_FILE" in os.environ:
        logging_cfg["file"] = os.environ["LOG_FILE"]

    # Security
    if "REQUIRE_AUTH" in os.environ:
        security_cfg["require_auth"] = _parse_bool(os.environ["REQUIRE_AUTH"])
    if "API_KEYS" in os.environ:
        security_cfg["api_keys"] = _parse_list(os.environ["API_KEYS"])
    if "RATE_LIMIT_REQUESTS" in os.environ:
        security_cfg["rate_limit_requests"] = int(os.environ["RATE_LIMIT_REQUESTS"])
    if "RATE_LIMIT_WINDOW" in os.environ:
        security_cfg["rate_limit_window"] = int(os.environ["RATE_LIMIT_WINDOW"])
    if "ENABLE_CORS" in os.environ:
        security_cfg["enable_cors"] = _parse_bool(os.environ["ENABLE_CORS"])
    if "CORS_ORIGINS" in os.environ:
        security_cfg["cors_origins"] = _parse_list(os.environ["CORS_ORIGINS"])
    if "ALLOWED_HOSTS" in os.environ:
        security_cfg["allowed_hosts"] = _parse_list(os.environ["ALLOWED_HOSTS"])

    # Network
    if "DEFAULT_TIMEOUT" in os.environ:
        network_cfg["default_timeout"] = int(os.environ["DEFAULT_TIMEOUT"])
    if "MAX_SCAN_TIMEOUT" in os.environ:
        network_cfg["nmap_scan_timeout"] = int(os.environ["MAX_SCAN_TIMEOUT"])

    return data


def load_config(config_path: Optional[str] = None) -> Config:
    """Load and validate configuration from JSON file and/or environment.

    Resolution order (later wins): built-in defaults, JSON file, environment
    variables (including a .env file).

    Args:
        config_path: Path to the JSON configuration file

    Returns:
        Config object containing validated configuration

    Raises:
        ValueError: If configuration is invalid or cannot be loaded
    """
    # Load a .env file into the environment if present (does not override
    # variables already set in the real environment).
    if load_dotenv is not None:
        load_dotenv()

    data: Dict[str, Any] = {}

    # Start from the JSON file when one is provided and exists.
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load config: {e}")

    # Overlay environment variables on top.
    try:
        data = _apply_env_overrides(data)
        return Config(**data)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to build configuration: {e}")
