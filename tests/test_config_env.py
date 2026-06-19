"""
Tests for environment-variable / .env configuration loading.

Covers the documented resolution order (defaults -> JSON file -> environment),
type coercion, and fail-loud handling of malformed values.
"""

import json
import os
import tempfile

import pytest

from netops_mcp.config.loader import load_config


def _json_file(data):
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(data, f)
    f.close()
    return f.name


class TestEnvOverrides:
    def test_env_applied_with_no_file(self, monkeypatch):
        monkeypatch.setenv("REQUIRE_AUTH", "true")
        monkeypatch.setenv("API_KEYS", "k1,k2")
        monkeypatch.setenv("RATE_LIMIT_REQUESTS", "7")
        monkeypatch.setenv("ENABLE_CORS", "true")
        monkeypatch.setenv("CORS_ORIGINS", "https://a.com,https://b.com")
        monkeypatch.setenv("ALLOWED_HOSTS", "a.com")

        config = load_config(None)

        assert config.security.require_auth is True
        assert config.security.api_keys == ["k1", "k2"]
        assert config.security.rate_limit_requests == 7
        assert config.security.enable_cors is True
        assert config.security.cors_origins == ["https://a.com", "https://b.com"]
        assert config.security.allowed_hosts == ["a.com"]

    def test_env_overrides_json(self, monkeypatch):
        path = _json_file(
            {"security": {"require_auth": False, "rate_limit_requests": 50}}
        )
        monkeypatch.setenv("REQUIRE_AUTH", "true")
        monkeypatch.setenv("RATE_LIMIT_REQUESTS", "7")
        try:
            config = load_config(path)
        finally:
            os.unlink(path)

        # Env wins over the file.
        assert config.security.require_auth is True
        assert config.security.rate_limit_requests == 7

    def test_json_used_when_env_absent(self, monkeypatch):
        monkeypatch.delenv("RATE_LIMIT_REQUESTS", raising=False)
        path = _json_file({"security": {"rate_limit_requests": 50}})
        try:
            config = load_config(path)
        finally:
            os.unlink(path)

        assert config.security.rate_limit_requests == 50

    def test_defaults_when_nothing_set(self, monkeypatch):
        monkeypatch.delenv("REQUIRE_AUTH", raising=False)
        config = load_config(None)
        assert config.security.require_auth is False  # model default

    def test_api_keys_trimmed_and_empties_dropped(self, monkeypatch):
        monkeypatch.setenv("API_KEYS", "k1, k2 ,, k3")
        config = load_config(None)
        assert config.security.api_keys == ["k1", "k2", "k3"]

    @pytest.mark.parametrize("raw,expected", [
        ("true", True), ("1", True), ("yes", True), ("on", True),
        ("false", False), ("0", False), ("no", False), ("off", False),
    ])
    def test_bool_parsing(self, monkeypatch, raw, expected):
        monkeypatch.setenv("REQUIRE_AUTH", raw)
        assert load_config(None).security.require_auth is expected

    def test_invalid_int_fails_loud(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_REQUESTS", "not-a-number")
        with pytest.raises(ValueError):
            load_config(None)
