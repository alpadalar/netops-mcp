"""
Tests for AuthenticationMiddleware (SEC-06).

First-ever coverage for the authentication middleware. Pins the hashed-only
constant-time key validation contract:

- api_keys entries arrive as 'sha256:<64-hex>' digests (guaranteed by the
  SecurityConfig format validator); a key whose digest is stored validates.
- No plain keys and no raw entry list are retained on the middleware
  instance — only stripped digests.
- Missing key -> 401 with WWW-Authenticate; wrong key -> 403; exempt paths
  (/health, /metrics) pass without any key.

Tests carrying the token 'hashed' in their name capture the pre-refactor
dead path (incoming key hashed and compared against hash-of-digest) and the
plain-retention bug — they are RED until the middleware rewrite lands.
"""

import hashlib
from unittest.mock import Mock

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from netops_mcp.middleware.auth import AuthenticationMiddleware

PLAIN_KEY = "test-key-123"
STORED_DIGEST = "sha256:" + hashlib.sha256(PLAIN_KEY.encode()).hexdigest()


def _build_app() -> Starlette:
    """Build a minimal Starlette app guarded by AuthenticationMiddleware."""

    async def homepage(request):
        return PlainTextResponse("ok")

    async def health(request):
        return PlainTextResponse("healthy")

    app = Starlette(routes=[Route("/", homepage), Route("/health", health)])
    app.add_middleware(
        AuthenticationMiddleware,
        api_keys=[STORED_DIGEST],
        require_auth=True,
    )
    return app


class TestValidateApiKey:
    """Direct unit tests for key storage and _validate_api_key."""

    def test_hashed_stored_key_validates(self):
        """A key whose sha256 digest is stored as 'sha256:<hex>' must validate."""
        mw = AuthenticationMiddleware(app=Mock(), api_keys=[STORED_DIGEST])
        assert mw._validate_api_key(PLAIN_KEY) is True

    def test_wrong_key_rejected_hashed(self):
        """A key not matching any stored digest must be rejected."""
        mw = AuthenticationMiddleware(app=Mock(), api_keys=[STORED_DIGEST])
        assert mw._validate_api_key("wrong-key") is False

    def test_no_plain_retention_hashed(self):
        """The middleware must retain no raw entries and no plain keys.

        Post-refactor contract: only stripped digests live on the instance
        (e.g. `_digests`); the raw `api_keys` list and the derived
        `hashed_keys` set are both gone.
        """
        mw = AuthenticationMiddleware(app=Mock(), api_keys=[STORED_DIGEST])
        assert not hasattr(mw, "api_keys")
        assert not hasattr(mw, "hashed_keys")


class TestAuthMiddlewareHTTP:
    """TestClient integration over a minimal Starlette app."""

    def test_missing_key_returns_401_with_www_authenticate(self):
        """No key at all -> 401 and the WWW-Authenticate header is present."""
        client = TestClient(_build_app())
        response = client.get("/")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

    def test_wrong_key_returns_403(self):
        """A wrong key -> 403 (key was provided but is invalid)."""
        client = TestClient(_build_app())
        response = client.get("/", headers={"Authorization": "Bearer wrong-key"})
        assert response.status_code == 403

    def test_valid_key_bearer_header_hashed(self):
        """Valid plain key via Authorization: Bearer -> 200."""
        client = TestClient(_build_app())
        response = client.get("/", headers={"Authorization": f"Bearer {PLAIN_KEY}"})
        assert response.status_code == 200

    def test_valid_key_x_api_key_header_hashed(self):
        """Valid plain key via X-API-Key -> 200."""
        client = TestClient(_build_app())
        response = client.get("/", headers={"X-API-Key": PLAIN_KEY})
        assert response.status_code == 200

    def test_valid_key_api_key_header_hashed(self):
        """Valid plain key via API-Key -> 200."""
        client = TestClient(_build_app())
        response = client.get("/", headers={"API-Key": PLAIN_KEY})
        assert response.status_code == 200

    def test_exempt_health_path_passes_without_key(self):
        """/health is exempt by default and needs no key."""
        client = TestClient(_build_app())
        response = client.get("/health")
        assert response.status_code == 200
