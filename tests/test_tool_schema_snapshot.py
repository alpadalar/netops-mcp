"""Golden JSON-schema snapshot tests locking the 26-tool MCP surface.

These tests capture the names, descriptions, and inputSchemas of all 26 tools
registered by BOTH servers (stdio ``server.py`` and HTTP ``server_http.py``)
and compare them against committed golden files under ``tests/fixtures/``.

Golden files are NEVER hand-edited. To regenerate after an intentional,
reviewed schema change:

    UPDATE_SNAPSHOTS=1 uv run pytest tests/test_tool_schema_snapshot.py --no-cov

The raw goldens stay per-server because the two FastMCP implementations
legitimately differ (stdio adds property-level descriptions and a schema-root
``title``); the cross-server test compares NORMALIZED schemas only.
"""

import asyncio
import json
import os
from contextlib import ExitStack
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Tuple
from unittest.mock import patch

FIXTURES = Path(__file__).parent / "fixtures"
STDIO_GOLDEN = FIXTURES / "tool_schemas_stdio.json"
HTTP_GOLDEN = FIXTURES / "tool_schemas_http.json"

EXPECTED_TOOL_COUNT = 26

# Fake system-check results so server constructors do not fork ~15 subprocesses.
FAKE_TOOL_STATUS: Dict[str, Any] = {
    "all_available": True,
    "available_tools": [],
    "missing_tools": [],
}
FAKE_SYSTEM_INFO: Dict[str, Any] = {
    "platform": "Linux",
    # platform_version is REQUIRED (WR-07): server.py's
    # _test_system_requirements reads it; omitting it made server
    # construction silently exercise the swallowed-KeyError path
    # (the exact fixture drift BUG-02 guarded against, see
    # tests/test_server.py FAKE_SYSTEM_INFO discipline).
    "platform_version": "6.0.0-test",
    "python_version": "3.11",
    "architecture": "x86_64",
    "hostname": "test",
    "cpu_count": 4,
    "memory_total": 1,
}


def _build_servers() -> Tuple[Any, Any]:
    """Instantiate both servers with system checks patched out.

    Patch targets are the IMPORTING module's bindings (``server.py`` aliases the
    checker as ``check_tools_status``) — patching
    ``netops_mcp.utils.system_check.check_required_tools`` would silently no-op.
    Phase 3 (03-01) extracted the tool closures into ``netops_mcp.tools.registry``,
    so the ``check_required_tools`` / ``health`` closures now resolve
    ``check_tools_status`` / ``get_system_info`` in the registry module — those
    bindings are patched here too. The HTTP server's PERF-03 startup cache
    (``self._tool_status_cache = check_tools_status()``) resolves the
    ``server_http.check_tools_status`` binding, patched here so construction
    forks no subprocesses. (03-04 deleted ``_setup_health_check`` — the daemon
    thread that used to fork ~15 subprocesses every 30s — so its former patch
    line is gone; patching a deleted attribute would raise AttributeError.)
    """
    patches = [
        patch("netops_mcp.server.check_tools_status", return_value=FAKE_TOOL_STATUS),
        patch("netops_mcp.server.get_system_info", return_value=FAKE_SYSTEM_INFO),
        patch("netops_mcp.server_http.check_tools_status", return_value=FAKE_TOOL_STATUS),
        patch("netops_mcp.tools.registry.check_tools_status", return_value=FAKE_TOOL_STATUS),
        patch("netops_mcp.tools.registry.get_system_info", return_value=FAKE_SYSTEM_INFO),
    ]
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        from netops_mcp.server import NetOpsMCPServer
        from netops_mcp.server_http import NetOpsMCPHTTPServer

        return NetOpsMCPServer(), NetOpsMCPHTTPServer()


def _stdio_snapshot(server: Any) -> Dict[str, Dict[str, Any]]:
    """Extract {name: {description, inputSchema}} from the SDK FastMCP (stdio) server."""
    tools = asyncio.run(server.mcp.list_tools())  # list[mcp.types.Tool]
    return {t.name: {"description": t.description, "inputSchema": t.inputSchema} for t in tools}


def _http_snapshot(server: Any) -> Dict[str, Dict[str, Any]]:
    """Extract {name: {description, inputSchema}} from the fastmcp 2.x (HTTP) server."""

    async def _get() -> Dict[str, Any]:
        tools = await server.mcp.get_tools()  # dict[str, FunctionTool]
        return {name: tool.to_mcp_tool() for name, tool in tools.items()}

    mcp_tools = asyncio.run(_get())
    return {
        name: {"description": tool.description, "inputSchema": tool.inputSchema}
        for name, tool in mcp_tools.items()
    }


@lru_cache(maxsize=1)
def _snapshots() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Build both servers once per test session and cache their snapshots."""
    stdio_server, http_server = _build_servers()
    return _stdio_snapshot(stdio_server), _http_snapshot(http_server)


def _canonical(snapshot: Dict[str, Dict[str, Any]]) -> str:
    """Canonical serialization: sorted keys, 2-space indent, trailing newline."""
    return json.dumps(snapshot, indent=2, sort_keys=True) + "\n"


def _assert_or_update(snapshot: Dict[str, Dict[str, Any]], golden_path: Path) -> None:
    """Compare snapshot against the golden file; rewrite it under UPDATE_SNAPSHOTS=1."""
    text = _canonical(snapshot)
    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(text)
    assert golden_path.exists(), (
        f"Golden file {golden_path.name} missing. Generate it with "
        "UPDATE_SNAPSHOTS=1 pytest tests/test_tool_schema_snapshot.py"
    )
    assert golden_path.read_text() == text, (
        f"Tool schema drift vs {golden_path.name}. The 26-tool MCP surface is locked; "
        "if this change is intentional and reviewed, regen with "
        "UPDATE_SNAPSHOTS=1 pytest tests/test_tool_schema_snapshot.py"
    )


def _normalize(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Strip the two legitimate cross-server differences before comparison.

    stdio (SDK FastMCP) adds per-property ``description`` (from Annotated Field
    signatures) and a schema-root ``title``; fastmcp 2.x does not. Everything
    else (property names, types, defaults, required lists) must match exactly.
    """
    normalized: Dict[str, Any] = json.loads(json.dumps(schema))  # deep copy
    normalized.pop("title", None)
    for prop in normalized.get("properties", {}).values():
        prop.pop("description", None)
        prop.pop("title", None)
    return normalized


def test_stdio_schema_matches_golden() -> None:
    stdio_snap, _ = _snapshots()
    _assert_or_update(stdio_snap, STDIO_GOLDEN)


def test_http_schema_matches_golden() -> None:
    _, http_snap = _snapshots()
    _assert_or_update(http_snap, HTTP_GOLDEN)


def test_both_servers_register_26_tools() -> None:
    stdio_snap, http_snap = _snapshots()
    assert len(stdio_snap) == EXPECTED_TOOL_COUNT, sorted(stdio_snap)
    assert len(http_snap) == EXPECTED_TOOL_COUNT, sorted(http_snap)
    assert set(stdio_snap) == set(http_snap)


def test_stdio_and_http_registrations_agree() -> None:
    stdio_snap, http_snap = _snapshots()
    assert set(stdio_snap) == set(http_snap)
    for name in sorted(stdio_snap):
        assert stdio_snap[name]["description"] == http_snap[name]["description"], name
        assert _normalize(stdio_snap[name]["inputSchema"]) == _normalize(
            http_snap[name]["inputSchema"]
        ), name
