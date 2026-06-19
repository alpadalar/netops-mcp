"""
Tests for the rate limiting middleware.

Focus: the sliding-window limit enforcement and the idle-bucket eviction that
bounds memory when clients/IPs rotate (regression coverage for the eviction
fix that drops empty buckets and periodically sweeps stale ones).
"""

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from netops_mcp.middleware.rate_limiter import RateLimiter, RateLimitMiddleware


@pytest.fixture
def clock(monkeypatch):
    """Deterministic, advanceable clock for the rate limiter."""
    holder = {"t": 1000.0}
    monkeypatch.setattr(
        "netops_mcp.middleware.rate_limiter.time.time", lambda: holder["t"]
    )
    return holder


class TestRateLimiterAccounting:
    """Sliding-window allow/deny accounting."""

    def test_allows_up_to_the_limit(self, clock):
        rl = RateLimiter(requests_per_window=3, window_seconds=60)
        for _ in range(3):
            allowed, remaining, _reset = rl.is_allowed("ip:1.1.1.1")
            assert allowed
        # remaining counts down to 0 on the last allowed request
        assert remaining == 0

    def test_blocks_over_the_limit(self, clock):
        rl = RateLimiter(requests_per_window=2, window_seconds=60)
        rl.is_allowed("ip:1.1.1.1")
        rl.is_allowed("ip:1.1.1.1")

        allowed, remaining, reset_time = rl.is_allowed("ip:1.1.1.1")
        assert allowed is False
        assert remaining == 0
        assert reset_time > 0

    def test_window_resets_after_expiry(self, clock):
        rl = RateLimiter(requests_per_window=2, window_seconds=60)
        rl.is_allowed("ip:1.1.1.1")
        rl.is_allowed("ip:1.1.1.1")
        assert rl.is_allowed("ip:1.1.1.1")[0] is False

        # Advance past the window; the old timestamps age out and requests flow.
        clock["t"] += 61
        assert rl.is_allowed("ip:1.1.1.1")[0] is True


class TestRateLimiterEviction:
    """Memory must stay bounded as clients/IPs rotate (the eviction fix)."""

    def test_empty_bucket_is_dropped(self, clock):
        rl = RateLimiter(requests_per_window=5, window_seconds=60)
        rl.is_allowed("ip:a")
        assert "ip:a" in rl.requests

        # Once the only request ages out, the bucket is removed, not left as [].
        clock["t"] += 61
        rl._cleanup_old_requests("ip:a", clock["t"])
        assert "ip:a" not in rl.requests

    def test_rotating_clients_are_swept(self, clock):
        rl = RateLimiter(requests_per_window=5, window_seconds=60)

        # 50 one-shot clients in the same instant: the first call prunes the
        # empty map, the rest record without pruning -> 50 live buckets.
        for i in range(50):
            rl.is_allowed(f"ip:10.0.0.{i}")
        assert len(rl.requests) == 50

        # Advance past the window so the periodic sweep fires on the next
        # request; every stale bucket is evicted, leaving only the new client.
        clock["t"] += 61
        rl.is_allowed("ip:fresh")
        assert len(rl.requests) == 1
        assert "ip:fresh" in rl.requests

    def test_active_client_survives_sweep_that_evicts_idle(self, clock):
        rl = RateLimiter(requests_per_window=10, window_seconds=60)

        rl.is_allowed("ip:idle")       # last seen at t0
        rl.is_allowed("ip:active")     # also t0

        clock["t"] += 50               # still inside the window: no sweep
        rl.is_allowed("ip:active")     # active now has a recent timestamp

        clock["t"] += 51               # crosses the window -> sweep fires
        rl.is_allowed("ip:active")

        # idle aged out entirely; active kept because it had an in-window hit.
        assert "ip:idle" not in rl.requests
        assert "ip:active" in rl.requests


def _build_app(limit):
    async def ok(_request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/api", ok), Route("/health", ok)])
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_window=limit,
        window_seconds=60,
        exempt_paths={"/health", "/metrics"},
    )
    return app


class TestRateLimitMiddleware:
    """End-to-end dispatch behaviour, including the exempt-path invariant."""

    def test_returns_429_once_limit_exceeded(self):
        client = TestClient(_build_app(limit=1))
        assert client.get("/api").status_code == 200
        blocked = client.get("/api")
        assert blocked.status_code == 429
        assert blocked.headers["X-RateLimit-Remaining"] == "0"

    def test_health_path_is_exempt(self):
        client = TestClient(_build_app(limit=1))
        # Far more than the limit, but /health is never rate limited.
        for _ in range(5):
            assert client.get("/health").status_code == 200
