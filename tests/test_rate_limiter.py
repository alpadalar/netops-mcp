"""
Tests for the async sliding-window RateLimiter (PERF-02 / TEST-06).

Pins the async rate-limiter contract deterministically:

- is_allowed is a coroutine guarded by an asyncio.Lock (PERF-02): it no
  longer blocks the event loop with a threading.Lock.
- The sliding window is driven by an injectable time_func clock (TEST-06),
  so over-limit rejection and window expiry are provable without any
  wall-clock waits. This whole module sleeps for zero real seconds.

Every test injects a mutable clock via time_func and advances it by hand;
coroutines are driven with asyncio.run so the tests stay sync-shaped under
pytest's strict asyncio mode.
"""

import asyncio
import inspect

from netops_mcp.middleware.rate_limiter import RateLimiter


class TestRateLimiter:
    """Deterministic behavior of the async sliding-window rate limiter."""

    def test_over_limit_no_sleep(self):
        """First two requests pass, the third is rejected — no sleeping."""
        clock = {"t": 1000.0}
        rl = RateLimiter(
            requests_per_window=2,
            window_seconds=60,
            time_func=lambda: clock["t"],
        )

        assert asyncio.run(rl.is_allowed("c"))[0] is True
        assert asyncio.run(rl.is_allowed("c"))[0] is True
        assert asyncio.run(rl.is_allowed("c"))[0] is False

    def test_sliding_window_expiry(self):
        """Advancing the injected clock past the window resets the limit."""
        clock = {"t": 1000.0}
        rl = RateLimiter(
            requests_per_window=2,
            window_seconds=60,
            time_func=lambda: clock["t"],
        )

        # Reach the limit within the window.
        assert asyncio.run(rl.is_allowed("c"))[0] is True
        assert asyncio.run(rl.is_allowed("c"))[0] is True
        assert asyncio.run(rl.is_allowed("c"))[0] is False

        # Advance past the window: the oldest requests fall out and the
        # limiter admits traffic again — deterministic, no wall-clock wait.
        clock["t"] += 61
        assert asyncio.run(rl.is_allowed("c"))[0] is True

    def test_is_allowed_is_coroutine(self):
        """is_allowed is async (asyncio.Lock, non-blocking hot path)."""
        assert inspect.iscoroutinefunction(RateLimiter.is_allowed)

    def test_remaining_count_decrements(self):
        """The remaining-request count decreases with each admitted call."""
        clock = {"t": 500.0}
        rl = RateLimiter(
            requests_per_window=3,
            window_seconds=60,
            time_func=lambda: clock["t"],
        )

        allowed_1, remaining_1, _ = asyncio.run(rl.is_allowed("c"))
        allowed_2, remaining_2, _ = asyncio.run(rl.is_allowed("c"))

        assert allowed_1 is True and remaining_1 == 2
        assert allowed_2 is True and remaining_2 == 1

    def test_reset_time_reflects_oldest_request(self):
        """When over limit the reset_time counts down from the oldest hit."""
        clock = {"t": 2000.0}
        rl = RateLimiter(
            requests_per_window=1,
            window_seconds=60,
            time_func=lambda: clock["t"],
        )

        assert asyncio.run(rl.is_allowed("c"))[0] is True

        # 10s later, still inside the window: rejected with ~50s to reset.
        clock["t"] += 10
        allowed, remaining, reset_time = asyncio.run(rl.is_allowed("c"))
        assert allowed is False
        assert remaining == 0
        assert reset_time == 50

    def test_clients_are_isolated(self):
        """Separate client_ids maintain independent windows."""
        clock = {"t": 0.0}
        rl = RateLimiter(
            requests_per_window=1,
            window_seconds=60,
            time_func=lambda: clock["t"],
        )

        assert asyncio.run(rl.is_allowed("client-a"))[0] is True
        # A different client is unaffected by client-a hitting its limit.
        assert asyncio.run(rl.is_allowed("client-b"))[0] is True
        assert asyncio.run(rl.is_allowed("client-a"))[0] is False

    def test_get_stats_is_async_and_reports_usage(self):
        """get_stats is a coroutine and reflects admitted requests."""
        assert inspect.iscoroutinefunction(RateLimiter.get_stats)

        clock = {"t": 100.0}
        rl = RateLimiter(
            requests_per_window=5,
            window_seconds=60,
            time_func=lambda: clock["t"],
        )

        asyncio.run(rl.is_allowed("c"))
        asyncio.run(rl.is_allowed("c"))
        stats = asyncio.run(rl.get_stats("c"))

        assert stats == {
            "limit": 5,
            "remaining": 3,
            "used": 2,
            "window_seconds": 60,
        }


class TestBucketEviction:
    """Idle client buckets are evicted so the map stays bounded (SEC-*)."""

    @staticmethod
    def _limiter(clock, **kwargs):
        return RateLimiter(time_func=lambda: clock["t"], **kwargs)

    def test_empty_bucket_is_dropped_not_kept(self):
        """A client whose requests all age out leaves no bucket behind."""
        clock = {"t": 1000.0}
        rl = self._limiter(clock, requests_per_window=5, window_seconds=60)

        asyncio.run(rl.is_allowed("c"))
        assert "c" in rl.requests

        # Past the window: the stale timestamp is dropped along with the
        # bucket itself, then the new request re-creates it with one entry.
        clock["t"] += 61
        asyncio.run(rl.is_allowed("c"))
        assert rl.requests["c"] == [clock["t"]]

    def test_rotating_clients_do_not_grow_the_map(self):
        """The periodic sweep evicts clients that never come back."""
        clock = {"t": 1000.0}
        rl = self._limiter(clock, requests_per_window=5, window_seconds=60)

        # 50 one-shot clients, each seen once and never again.
        for i in range(50):
            asyncio.run(rl.is_allowed(f"ip:10.0.0.{i}"))
        assert len(rl.requests) == 50

        # Advance past the window so the next request triggers the sweep.
        clock["t"] += 61
        asyncio.run(rl.is_allowed("ip:10.0.1.1"))

        # Every stale bucket is gone; only the current caller remains.
        assert set(rl.requests) == {"ip:10.0.1.1"}

    def test_sweep_preserves_active_clients(self):
        """A client with in-window traffic survives the sweep with its count."""
        clock = {"t": 1000.0}
        rl = self._limiter(clock, requests_per_window=5, window_seconds=60)

        asyncio.run(rl.is_allowed("stale"))

        # Move most of the way through the window, then keep 'active' busy.
        clock["t"] += 40
        asyncio.run(rl.is_allowed("active"))

        # Cross the sweep threshold: 'stale' has aged out, 'active' has not.
        clock["t"] += 25
        asyncio.run(rl.is_allowed("other"))

        assert "stale" not in rl.requests
        assert rl.requests["active"] == [1040.0]

    def test_sweep_does_not_reset_an_active_limit(self):
        """Eviction must not hand a throttled client a fresh allowance."""
        clock = {"t": 1000.0}
        rl = self._limiter(clock, requests_per_window=2, window_seconds=60)

        assert asyncio.run(rl.is_allowed("c"))[0] is True
        assert asyncio.run(rl.is_allowed("c"))[0] is True

        # Far enough for the sweep to run, but still inside c's window.
        clock["t"] += 59
        assert asyncio.run(rl.is_allowed("c"))[0] is False

    def test_get_stats_does_not_resurrect_a_bucket(self):
        """Reading stats for an unknown client must not create a bucket."""
        clock = {"t": 1000.0}
        rl = self._limiter(clock, requests_per_window=5, window_seconds=60)

        stats = asyncio.run(rl.get_stats("never-seen"))

        assert stats["used"] == 0
        assert rl.requests == {}
