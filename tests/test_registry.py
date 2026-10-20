"""Tests for the registration-derived tool count in ``tools/registry.py``.

REF-05: the 26-tool count is derived from the registrations themselves (no
reliance on FastMCP private internals, which changed between majors).
"""

from unittest.mock import MagicMock

from netops_mcp.tools.registry import register_tools


def test_register_tools_returns_dynamic_count_30():
    """REF-05: registering the shared surface yields the dynamic count 30."""
    from fastmcp import FastMCP

    mcp = FastMCP("count-probe")
    count = register_tools(mcp, MagicMock())
    assert count == 30


def test_registered_tools_visible_on_fastmcp_instance():
    """The count matches what the FastMCP instance actually lists."""
    import asyncio

    from fastmcp import FastMCP

    mcp = FastMCP("list-probe")
    count = register_tools(mcp, MagicMock())
    assert len(asyncio.run(mcp.list_tools())) == count
