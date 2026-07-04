"""
Tests for MetricsCollector bounded accumulation (PERF-01).

Proves two properties of the metrics store after the unbounded
``defaultdict(list)`` duration accumulators are replaced with running
sum + count scalars:

- ``test_duration_storage_is_bounded``: memory stays O(label cardinality)
  — HTTP request and tool-execution durations are kept as a float sum and
  an int count, never a per-sample list. After N records for one label the
  count scalar equals N and no per-sample list attribute survives.
- ``test_export_byte_compatible``: the Prometheus text-format export is
  byte-identical to the pre-refactor ``_sum``/``_count`` line format for the
  same input sequence (PERF-01 changed the memory model, not the output).

A FRESH ``MetricsCollector()`` is built per test (via ``setup_method``) — the
module-level ``metrics_collector`` singleton accumulates process-wide and
would make absolute-value assertions non-deterministic.
"""

from netops_mcp.middleware.metrics import MetricsCollector


class TestMetricsCollector:
    """Bounded scalar accumulation + byte-compatible Prometheus export."""

    def setup_method(self):
        """Build a fresh collector so state never bleeds across tests."""
        self.collector = MetricsCollector()

    def test_export_byte_compatible(self):
        """Scalar accumulation emits the exact pre-refactor _sum/_count lines."""
        # Two HTTP requests for one label: sum 0.5+1.5=2.0, count 2.
        self.collector.record_http_request("GET", "/x", 200, 0.5)
        self.collector.record_http_request("GET", "/x", 200, 1.5)
        # Two tool executions for one tool: sum 0.25+0.75=1.0, count 2.
        self.collector.record_tool_execution("ping", 0.25, True)
        self.collector.record_tool_execution("ping", 0.75, True)

        export = self.collector.export_prometheus()

        # Exact Prometheus text-format lines the list-based export produced.
        assert (
            'http_request_duration_seconds_sum{method="GET",path="/x",status="200"} 2.000000'
            in export
        )
        assert (
            'http_request_duration_seconds_count{method="GET",path="/x",status="200"} 2' in export
        )
        assert 'tool_execution_duration_seconds_sum{tool="ping"} 1.000000' in export
        assert 'tool_execution_duration_seconds_count{tool="ping"} 2' in export

        # HELP/TYPE histogram headers are preserved so the export byte-matches.
        assert "# TYPE http_request_duration_seconds histogram" in export
        assert "# TYPE tool_execution_duration_seconds histogram" in export

    def test_duration_storage_is_bounded(self):
        """Durations accumulate as sum+count scalars, never a per-sample list."""
        n = 1000
        key = ("GET", "/api", 200)
        for _ in range(n):
            self.collector.record_http_request("GET", "/api", 200, 0.01)
        for _ in range(n):
            self.collector.record_tool_execution("ping", 0.01, True)

        # HTTP: scalar count equals number of records; sum is a float scalar.
        assert self.collector.http_request_duration_count[key] == n
        assert isinstance(self.collector.http_request_duration_sum[key], float)

        # Tool: same bounded shape.
        assert self.collector.tool_execution_duration_count["ping"] == n
        assert isinstance(self.collector.tool_execution_duration_sum["ping"], float)

        # No per-sample list is retained after N records.
        assert not hasattr(self.collector, "http_request_duration_seconds")
        assert not hasattr(self.collector, "tool_execution_duration")
