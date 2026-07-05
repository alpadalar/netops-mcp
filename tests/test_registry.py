"""Guard tests for the dynamic tool-count coupling in ``tools/registry.py``.

REF-05 derives the 26-tool count dynamically from the FastMCP instance instead
of hardcoding the literal. WR-03: that derivation reaches into the private
``_tool_manager._tools`` mapping because neither FastMCP class exposes a SYNC
public accessor that works uniformly (the SDK's ``_tool_manager.list_tools()``
is sync, fastmcp's is a coroutine). The access is wrapped defensively so an
upstream rename degrades to ``0`` rather than raising ``AttributeError`` at
runtime — and the guard test below fails LOUDLY in CI if the private path
disappears on an SDK bump, so REF-05 never silently reports a zero tool count.
"""

from unittest.mock import MagicMock

from netops_mcp.tools.registry import _registered_tool_count, register_tools


def test_private_tool_manager_path_exists_on_both_fastmcp_classes():
    """WR-03 CI guard: both FastMCP classes still expose _tool_manager._tools.

    If a future SDK/fastmcp upgrade renames either attribute, this test goes RED
    in CI — the loud, early signal that the REF-05 dynamic count must migrate to
    a new accessor, instead of silently degrading to 0 in production.
    """
    from fastmcp import FastMCP as StandaloneFastMCP
    from mcp.server.fastmcp import FastMCP as SDKFastMCP

    for cls in (SDKFastMCP, StandaloneFastMCP):
        inst = cls("wr03-guard-probe")
        assert hasattr(inst, "_tool_manager"), (
            f"{cls.__module__}.{cls.__qualname__} no longer exposes _tool_manager; "
            "REF-05 dynamic tool-count coupling broke on an SDK upgrade"
        )
        assert hasattr(inst._tool_manager, "_tools"), (
            f"{cls.__module__}.{cls.__qualname__}._tool_manager no longer exposes "
            "_tools; migrate _registered_tool_count to a new accessor"
        )


def test_register_tools_returns_dynamic_count_26():
    """REF-05: registering the shared surface yields the dynamic count 26.

    ``register_tools`` only uses the ``mcp`` decorator surface at registration
    time; the ``tools`` holder is dereferenced lazily inside each closure (tool
    invocation), so a MagicMock stands in here. The returned count flows through
    the defensive ``_registered_tool_count`` helper on a REAL fastmcp instance.
    """
    from fastmcp import FastMCP

    mcp = FastMCP("wr03-count-probe")
    count = register_tools(mcp, MagicMock())
    assert count == 26


def test_registered_tool_count_degrades_gracefully_on_missing_internals():
    """WR-03: defensive fallback returns 0 (never raises) when internals vanish."""

    # No _tool_manager at all.
    assert _registered_tool_count(object()) == 0

    # _tool_manager present but _tools missing.
    class MgrOnly:
        _tool_manager = object()

    assert _registered_tool_count(MgrOnly()) == 0

    # _tools present but not sized (defensive TypeError guard).
    class BadTools:
        class _mgr:
            _tools = 123

        _tool_manager = _mgr

    assert _registered_tool_count(BadTools()) == 0


def test_registered_tool_count_reads_len_of_tools_mapping():
    """WR-03: with a real ``_tool_manager._tools`` mapping, count is its len."""

    class FakeMgr:
        _tools = {"a": 1, "b": 2, "c": 3}

    class FakeMcp:
        _tool_manager = FakeMgr()

    assert _registered_tool_count(FakeMcp()) == 3
