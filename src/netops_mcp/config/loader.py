"""
Configuration loading utilities for the NetOps MCP server.

This module handles loading and validation of server configuration:
- JSON configuration file loading
- Environment variable handling
- Configuration validation using Pydantic models
- Error handling for invalid configurations
"""

import json
import os
from typing import Optional
from .models import Config


def load_config(config_path: Optional[str] = None) -> Config:
    """Load and validate configuration from JSON file or environment.

    Args:
        config_path: Path to the JSON configuration file

    Returns:
        Config object containing validated configuration

    Raises:
        ValueError: If configuration is invalid or missing required fields
    """
    # If a config path is provided, load from JSON file
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path) as f:
                config_data = json.load(f)
                return Config(**config_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load config: {e}")

    # Otherwise, use default configuration
    return Config()
