"""Live-uvicorn E2E middleware harness (TEST-02, REF-07, PERF-03).

Proves the middleware stack and the ``/health`` + ``/metrics`` routes are
attached to the ACTUALLY-served app — the one uvicorn serves — rather than a
throwaway ``http_app()``. Every test runs against a REAL uvicorn server on an
ephemeral port (``live_server`` / ``live_server_factory`` fixtures in
``conftest.py``); none uses Starlette's in-process ASGI test client, which can
pass even when the served-app wiring is wrong (RESEARCH anti-pattern — an
in-process client bypasses the real serve path).

Anti-tautology / RED-on-detach guarantee: ``test_no_key_returns_401`` only
passes because ``AuthenticationMiddleware`` sits on the served app. Removing the
``AuthenticationMiddleware`` entry from ``NetOpsMCPHTTPServer.build_http_app()``
(the Phase 2 CR-01 throwaway-app regression) lets an unauthenticated MCP request
reach the handler (400 MCP session negotiation, not 401), turning this suite
RED. ``test_auth_middleware_on_the_served_app`` encodes that invariant
explicitly by asserting the middleware class is present on the built app's
stack.
"""

import hashlib

import httpx
import pytest

from netops_mcp.middleware.auth import AuthenticationMiddleware
from netops_mcp.middleware.rate_limiter import RateLimitMiddleware

MCP_PATH = "/netops-mcp"
_MCP_HEADERS = {"Accept": "application/json, text/event-stream"}
_LIST_TOOLS = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}


def _http_requests_total(metrics_text: str) -> int:
    """Sum every ``http_requests_total{...}`` counter sample in a Prometheus dump.

    Deltas only (RESEARCH Pitfall 6): ``metrics_collector`` is a process-wide
    singleton, so absolute values bleed across tests — callers compare a
    before/after delta, never an absolute count.
    """
    total = 0
    for line in metrics_text.splitlines():
        if line.startswith("http_requests_total{"):
            total += int(line.rsplit(" ", 1)[1])
    return total


def test_no_key_returns_401(live_server):
    """An unauthenticated MCP request is rejected by AuthenticationMiddleware (401)."""
    base_url, _key, _server = live_server
    response = httpx.post(
        base_url + MCP_PATH, json=_LIST_TOOLS, headers=_MCP_HEADERS, timeout=5
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_valid_key_lists_tools(live_server):
    """A valid Bearer key completes the MCP handshake and lists all 26 tools.

    Uses ``fastmcp.Client`` (full initialize + session negotiation) so the
    200-path success is unambiguous: auth passed AND the served app IS the real
    MCP app, not a throwaway.
    """
    from fastmcp import Client
    from fastmcp.client.transports import StreamableHttpTransport

    base_url, key, _server = live_server
    transport = StreamableHttpTransport(
        url=base_url + MCP_PATH, headers={"Authorization": f"Bearer {key}"}
    )
    async with Client(transport) as client:
        tools = await client.list_tools()
    assert len(tools) == 26


def test_over_limit_returns_429(live_server_factory):
    """Authenticated requests over the window limit get 429 from RateLimitMiddleware."""
    with live_server_factory({"rate_limit_requests": 3, "rate_limit_window": 60}) as (
        base_url,
        key,
        _server,
    ):
        headers = {"Authorization": f"Bearer {key}", **_MCP_HEADERS}
        codes = [
            httpx.post(
                base_url + MCP_PATH, json=_LIST_TOOLS, headers=headers, timeout=5
            ).status_code
            for _ in range(6)
        ]
    assert 429 in codes


def test_metrics_counter_increments(live_server):
    """MetricsMiddleware on the served app counts a known request (delta-based).

    WR-02: /metrics is now auth-gated (only /health stays public), so the scrape
    requests carry the Bearer key; /health remains key-free.
    """
    base_url, key, _server = live_server
    metrics_headers = {"Authorization": f"Bearer {key}"}
    before = _http_requests_total(
        httpx.get(base_url + "/metrics", headers=metrics_headers, timeout=5).text
    )
    # /health is auth+rate exempt but IS counted by MetricsMiddleware.
    assert httpx.get(base_url + "/health", timeout=5).status_code == 200
    after = _http_requests_total(
        httpx.get(base_url + "/metrics", headers=metrics_headers, timeout=5).text
    )
    assert after > before


def test_metrics_requires_auth(live_server):
    """WR-02: unauthenticated /metrics is rejected; /health stays public.

    On the default 0.0.0.0 bind an open /metrics would disclose request
    paths/status/per-label counts to any origin. Gating it behind auth closes
    that net-new Phase 3 exposure; /health remains key-free for liveness probes.
    """
    base_url, key, _server = live_server
    # No key -> 401 from AuthenticationMiddleware.
    assert httpx.get(base_url + "/metrics", timeout=5).status_code == 401
    # Valid key -> 200 Prometheus dump.
    ok = httpx.get(
        base_url + "/metrics", headers={"Authorization": f"Bearer {key}"}, timeout=5
    )
    assert ok.status_code == 200
    assert "http_requests_total" in ok.text
    # /health is still reachable without a key.
    assert httpx.get(base_url + "/health", timeout=5).status_code == 200


def test_auth_middleware_on_the_served_app(live_server):
    """Anti-tautology guard: auth + rate-limit middleware live on the SERVED app.

    If ``build_http_app()`` ever stops attaching ``AuthenticationMiddleware``
    (the throwaway-app regression), this assertion — and
    ``test_no_key_returns_401`` — go RED. The api_key is stored as a
    ``sha256:<64-hex>`` digest (conftest ``E2E_KEY_DIGEST``); it is recomputed
    here to document the config contract.
    """
    _base_url, key, server = live_server
    expected_digest = "sha256:" + hashlib.sha256(key.encode()).hexdigest()
    assert len(expected_digest) == len("sha256:") + 64

    middleware_classes = [m.cls for m in server.build_http_app().user_middleware]
    assert AuthenticationMiddleware in middleware_classes
    assert RateLimitMiddleware in middleware_classes
