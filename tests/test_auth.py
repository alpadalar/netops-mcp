"""
Tests for the authentication middleware.

Focus: API keys are compared in constant time against the SHA-256 hash of every
configured key with no early exit (regression coverage for the timing-safe
comparison fix), plus the dispatch contract (401/403, Bearer/X-API-Key,
exempt paths).
"""

import hashlib
import hmac
from unittest.mock import Mock, patch

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from netops_mcp.middleware.auth import AuthenticationMiddleware


def _middleware(api_keys, require_auth=True):
    """Build a middleware instance with a throwaway downstream app."""
    return AuthenticationMiddleware(
        Starlette(),
        api_keys=api_keys,
        require_auth=require_auth,
        exempt_paths={"/health", "/metrics"},
    )


class TestKeyValidation:
    def test_valid_key_accepted(self):
        mw = _middleware(["secret-key"])
        assert mw._validate_api_key("secret-key") is True

    def test_invalid_key_rejected(self):
        mw = _middleware(["secret-key"])
        assert mw._validate_api_key("wrong-key") is False

    def test_keys_are_stored_hashed_not_plaintext(self):
        mw = _middleware(["secret-key"])
        # The raw secret is never kept in the comparison set; only its hash is.
        assert "secret-key" not in mw.hashed_keys
        assert hashlib.sha256(b"secret-key").hexdigest() in mw.hashed_keys

    def test_uses_constant_time_compare_for_every_key_no_early_exit(self):
        mw = _middleware(["key-a", "key-b", "key-c"])
        spy = Mock(wraps=hmac.compare_digest)
        with patch("netops_mcp.middleware.auth.hmac.compare_digest", spy):
            assert mw._validate_api_key("key-b") is True
        # All three keys are compared even after a match is found, so the work
        # (and timing) does not depend on which key matched.
        assert spy.call_count == 3

    def test_rejection_also_compares_against_all_keys(self):
        mw = _middleware(["key-a", "key-b", "key-c"])
        spy = Mock(wraps=hmac.compare_digest)
        with patch("netops_mcp.middleware.auth.hmac.compare_digest", spy):
            assert mw._validate_api_key("nope") is False
        assert spy.call_count == 3


def _build_app(api_keys, require_auth=True):
    async def ok(_request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/secure", ok), Route("/health", ok)])
    app.add_middleware(
        AuthenticationMiddleware,
        api_keys=api_keys,
        require_auth=require_auth,
        exempt_paths={"/health", "/metrics"},
    )
    return app


class TestAuthDispatch:
    def test_missing_key_returns_401(self):
        client = TestClient(_build_app(["secret"]))
        assert client.get("/secure").status_code == 401

    def test_invalid_key_returns_403(self):
        client = TestClient(_build_app(["secret"]))
        resp = client.get("/secure", headers={"Authorization": "Bearer wrong"})
        assert resp.status_code == 403

    def test_valid_bearer_token_allowed(self):
        client = TestClient(_build_app(["secret"]))
        resp = client.get("/secure", headers={"Authorization": "Bearer secret"})
        assert resp.status_code == 200

    def test_valid_x_api_key_header_allowed(self):
        client = TestClient(_build_app(["secret"]))
        resp = client.get("/secure", headers={"X-API-Key": "secret"})
        assert resp.status_code == 200

    def test_health_path_exempt_without_key(self):
        client = TestClient(_build_app(["secret"]))
        assert client.get("/health").status_code == 200

    def test_auth_disabled_allows_unauthenticated(self):
        client = TestClient(_build_app([], require_auth=False))
        assert client.get("/secure").status_code == 200
