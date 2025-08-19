"""
DevOps MCP Server - A Model Context Protocol server for DevOps and network diagnostic tools.

This package exposes symbols lazily to avoid import side-effects when
running `python -m netops_mcp.server`.
"""

from typing import TYPE_CHECKING

__version__ = "0.1.0"
__all__ = ["DevOpsMCPServer", "__version__"]

if TYPE_CHECKING:
    # For type checkers only; avoids runtime import
    from .server import DevOpsMCPServer as DevOpsMCPServer


def __getattr__(name):  # pragma: no cover - trivial lazy import
    if name == "DevOpsMCPServer":
        from .server import DevOpsMCPServer as _DevOpsMCPServer
        return _DevOpsMCPServer
    raise AttributeError(f"module 'netops_mcp' has no attribute {name!r}")
