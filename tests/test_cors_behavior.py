"""
Tests proving Starlette CORSMiddleware origin-reflection behavior.

These tests document WHY SecurityConfig rejects the wildcard-origins +
allow-credentials combination at config load time (SEC-04): Starlette
0.47.2 does NOT reject that combination — on preflight it REFLECTS the
arbitrary request origin back with credentials allowed, which exposes
credentialed responses cross-site.

The apps under test are built inline; nothing here imports the real
server (middleware wiring to the served app is Phase 3 REF-07 territory).
"""

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient


def _build_app(allow_origins: list, allow_credentials: bool) -> Starlette:
    """Build a minimal Starlette app with the given CORS configuration."""

    async def homepage(request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/x", homepage)])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


class TestCorsBehavior:
    """Prove reflection danger and explicit-origin safety on starlette 0.47.2."""

    def test_wildcard_with_credentials_reflects_arbitrary_origin(self):
        """Wildcard + credentials REFLECTS any request origin on preflight.

        This is the dangerous behavior SecurityConfig makes unrepresentable:
        Starlette does not raise on allow_origins=['*'] + allow_credentials=True;
        it reflects the caller-controlled Origin header back verbatim together
        with Access-Control-Allow-Credentials: true. Our guard must therefore
        live at config load time — the framework will not protect us.
        """
        app = _build_app(allow_origins=["*"], allow_credentials=True)
        client = TestClient(app)

        response = client.options(
            "/x",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )

        # REFLECTED: the arbitrary evil origin comes back as allowed
        assert response.headers["access-control-allow-origin"] == "https://evil.example"
        assert response.headers["access-control-allow-credentials"] == "true"

    def test_explicit_origins_do_not_reflect_disallowed(self):
        """Explicit origins: disallowed origins get NO ACAO; allowed get themselves."""
        app = _build_app(
            allow_origins=["http://localhost:3000"], allow_credentials=True
        )
        client = TestClient(app)

        # Disallowed evil origin: no access-control-allow-origin header at all
        evil_response = client.options(
            "/x",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" not in evil_response.headers

        # Allowed origin: gets exactly itself back
        ok_response = client.options(
            "/x",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert (
            ok_response.headers["access-control-allow-origin"]
            == "http://localhost:3000"
        )
