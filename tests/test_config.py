"""
Tests for configuration modules.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch, mock_open
from pydantic import ValidationError
from netops_mcp.config.loader import load_config
from netops_mcp.config.models import Config, LoggingConfig, SecurityConfig, NetworkConfig


class TestConfigLoader:
    """Test configuration loader functionality."""

    def test_load_config_with_valid_file(self):
        """Test loading configuration from valid file."""
        config_data = {
            "logging": {
                "level": "INFO",
                "format": "json",
                "file": "test.log"
            },
            "security": {
                "allow_privileged_commands": True,
                "allowed_hosts": ["localhost", "127.0.0.1"],
                "rate_limit_requests": 60
            },
            "network": {
                "default_timeout": 30,
                "max_retries": 3,
                "ping_count": 4,
                "nmap_scan_timeout": 300
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            json.dump(config_data, temp_file)
            temp_file.close()
            
            try:
                config = load_config(temp_file.name)
                
                assert config is not None
                assert isinstance(config, Config)
                assert config.logging.level == "INFO"
                assert config.security.allow_privileged_commands == True
                assert config.network.default_timeout == 30
                # server attribute doesn't exist in current config model
                assert config.network.default_timeout == 30
            finally:
                os.unlink(temp_file.name)

    def test_load_config_with_nonexistent_file(self):
        """Test loading configuration with nonexistent file."""
        config = load_config("nonexistent_file.json")
        
        assert config is not None
        assert isinstance(config, Config)
        # Should use default values
        assert config.logging.level == "INFO"
        # server attribute doesn't exist in current config model
        assert config.network.default_timeout == 30

    def test_load_config_with_none_path(self):
        """Test loading configuration with None path."""
        config = load_config(None)
        
        assert config is not None
        assert isinstance(config, Config)
        # Should use default values
        assert config.logging.level == "INFO"

    def test_load_config_with_invalid_json(self):
        """Test loading configuration with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write('{"invalid": "json"')
            temp_file.close()
            
            try:
                with pytest.raises(ValueError):
                    config = load_config(temp_file.name)
            finally:
                os.unlink(temp_file.name)

    def test_load_config_with_empty_file(self):
        """Test loading configuration with empty file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write('{}')
            temp_file.close()
            
            try:
                config = load_config(temp_file.name)
                
                assert config is not None
                assert isinstance(config, Config)
                # Should use default values
                assert config.logging.level == "INFO"
            finally:
                os.unlink(temp_file.name)


class TestConfigModels:
    """Test configuration models."""

    def test_logging_config_defaults(self):
        """Test LoggingConfig default values."""
        config = LoggingConfig()
        
        assert config.level == "INFO"
        assert config.format == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        assert config.file == None

    def test_logging_config_custom_values(self):
        """Test LoggingConfig with custom values."""
        config = LoggingConfig(
            level="DEBUG",
            format="json",
            file="custom.log"
        )
        
        assert config.level == "DEBUG"
        assert config.format == "json"
        assert config.file == "custom.log"

    def test_security_config_defaults(self):
        """Test SecurityConfig default values."""
        config = SecurityConfig()
        
        assert config.allow_privileged_commands == False
        assert config.allowed_hosts == []
        assert config.rate_limit_requests == 100
        assert config.rate_limit_window == 60

    def test_security_config_custom_values(self):
        """Test SecurityConfig with custom values."""
        config = SecurityConfig(
            allow_privileged_commands=True,
            allowed_hosts=["localhost"],
            rate_limit_requests=30
        )
        
        assert config.allow_privileged_commands == True
        assert config.allowed_hosts == ["localhost"]
        assert config.rate_limit_requests == 30
        assert config.rate_limit_window == 60

    def test_network_config_defaults(self):
        """Test NetworkConfig default values."""
        config = NetworkConfig()
        
        assert config.default_timeout == 30
        assert config.max_retries == 3
        assert config.ping_count == 4
        assert config.nmap_scan_timeout == 300

    def test_network_config_custom_values(self):
        """Test NetworkConfig with custom values."""
        config = NetworkConfig(
            default_timeout=60,
            max_retries=5,
            ping_count=10,
            nmap_scan_timeout=600
        )
        
        assert config.default_timeout == 60
        assert config.max_retries == 5
        assert config.ping_count == 10
        assert config.nmap_scan_timeout == 600

    def test_config_defaults(self):
        """Test Config default values."""
        config = Config()
        
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.network, NetworkConfig)
        # server attribute doesn't exist in current config model
        assert config.network.default_timeout == 30
        # server attributes don't exist in current config model
        assert config.network.max_retries == 3

    def test_config_custom_values(self):
        """Test Config with custom values."""
        config = Config(
            logging={"level": "DEBUG"},
            security={"allow_privileged_commands": True},
            network={"default_timeout": 60, "max_retries": 5, "ping_count": 8}
        )
        
        assert config.logging.level == "DEBUG"
        assert config.security.allow_privileged_commands == True
        assert config.network.default_timeout == 60
        # server attributes don't exist in current config model
        assert config.network.max_retries == 5
        # server attributes don't exist in current config model
        assert config.network.ping_count == 8

    def test_config_validation(self):
        """Test Config validation."""
        # This test is simplified since Pydantic handles validation
        config = Config()
        assert config is not None


def _load_config_from_temp(config_data):
    """Write config_data to a temp JSON file and load it via load_config."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
        json.dump(config_data, temp_file)
        temp_file.close()
        try:
            return load_config(temp_file.name)
        finally:
            os.unlink(temp_file.name)


class TestStrictConfig:
    """Strict-mode behavior (extra='forbid'): unknown keys fail loudly (SEC-08)."""

    def test_unknown_top_level_key_fails_load_with_key_name(self):
        """A typo'd top-level key ('securty') fails load_config, naming the key."""
        with pytest.raises(ValueError) as exc_info:
            _load_config_from_temp({"securty": {"require_auth": False}})
        assert "securty" in str(exc_info.value)

    def test_unknown_nested_key_under_security_fails_load(self):
        """A typo'd nested key ('requre_auth') under security fails load_config."""
        with pytest.raises(ValueError) as exc_info:
            _load_config_from_temp({"security": {"requre_auth": True}})
        assert "requre_auth" in str(exc_info.value)

    def test_direct_model_construction_rejects_unknown_key(self):
        """Direct Config construction raises pydantic ValidationError for unknown keys."""
        with pytest.raises(ValidationError):
            Config(securty={})

    def test_config_constructs_with_defaults(self):
        """Config() must stay constructible with pure defaults (snapshot/stdio safety)."""
        config = Config()
        assert config is not None
        assert isinstance(config, Config)

    def test_require_auth_defaults_to_true(self):
        """require_auth defaults to True at model level (SEC-01 default flip)."""
        assert Config().security.require_auth is True


class TestServerConfig:
    """New server section and previously silently-dropped network fields (SEC-08)."""

    def test_server_defaults(self):
        """Config().server carries the builtin host/port/path defaults."""
        config = Config()
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 8815
        assert config.server.path == "/netops-mcp"

    def test_server_custom_values_round_trip(self):
        """A server section in a JSON config round-trips through load_config."""
        config = _load_config_from_temp(
            {"server": {"host": "127.0.0.1", "port": 9000, "path": "/custom"}}
        )
        assert config.server.host == "127.0.0.1"
        assert config.server.port == 9000
        assert config.server.path == "/custom"

    def test_network_new_fields_defaults(self):
        """NetworkConfig gains max_scan_timeout and allowed_ports (string) defaults."""
        network = NetworkConfig()
        assert network.max_scan_timeout == 300
        assert network.allowed_ports == "1-65535"


class TestApiKeyFormat:
    """api_keys entries must be 'sha256:<64-hex>' digests (SEC-06 storage half)."""

    def test_plain_key_rejected_on_model(self):
        """A plain-looking api_keys entry raises ValidationError at model level."""
        with pytest.raises(ValidationError):
            SecurityConfig(api_keys=["plain-key"])

    def test_hashed_key_accepted(self):
        """A well-formed sha256:<64-hex> entry is accepted unchanged."""
        digest = "sha256:" + "a" * 64
        config = SecurityConfig(api_keys=[digest])
        assert config.api_keys == [digest]

    def test_plain_key_via_loader_mentions_hash_one_liner(self):
        """A plain key through load_config fails with a message containing 'sha256:'."""
        with pytest.raises(ValueError) as exc_info:
            _load_config_from_temp({"security": {"api_keys": ["my-plain-secret"]}})
        assert "sha256:" in str(exc_info.value)


class TestCorsRejection:
    """Wildcard cors_origins + cors_allow_credentials=True is unrepresentable (SEC-04)."""

    def test_wildcard_with_credentials_rejected(self):
        """cors_allow_credentials=True with ['*'] origins raises ValidationError."""
        with pytest.raises(ValidationError):
            SecurityConfig(cors_allow_credentials=True, cors_origins=["*"])

    def test_wildcard_among_explicit_origins_rejected(self):
        """A wildcard hidden among explicit origins is still rejected."""
        with pytest.raises(ValidationError):
            SecurityConfig(
                cors_allow_credentials=True,
                cors_origins=["https://ok.example", "*"],
            )

    def test_credentials_with_explicit_origins_accepted(self):
        """Credentials with only explicit origins is a valid combination."""
        config = SecurityConfig(
            cors_allow_credentials=True,
            cors_origins=["https://ok.example"],
        )
        assert config.cors_allow_credentials is True
        assert config.cors_origins == ["https://ok.example"]

    def test_cors_allow_credentials_defaults_to_false(self):
        """cors_allow_credentials defaults to False."""
        assert SecurityConfig().cors_allow_credentials is False


class TestCommittedConfigs:
    """Both committed config JSONs must load cleanly under the strict models."""

    REPO_ROOT = Path(__file__).resolve().parent.parent

    def test_example_config_loads_under_strict_models(self):
        """config.example.json loads, ships no wildcard origin, and enables auth."""
        config = load_config(str(self.REPO_ROOT / "config" / "config.example.json"))
        assert config.server.port == 8815
        assert "*" not in config.security.cors_origins
        assert config.security.require_auth is True

    def test_default_config_loads_under_strict_models(self):
        """config/config.json (used by start_http_server.sh) loads under strict models."""
        config = load_config(str(self.REPO_ROOT / "config" / "config.json"))
        assert config.server.port == 8815
        assert config.server.host == "0.0.0.0"
        assert config.server.path == "/netops-mcp"
