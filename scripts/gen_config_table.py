#!/usr/bin/env python3
"""
Config/env reference-table generator for NetOps MCP.

Derives the configuration table embedded in README.md directly from the
Pydantic models in ``netops_mcp.config.models``. Because every model is
``ConfigDict(extra='forbid')``, the model field set is the authoritative
contract; generating the table from ``Config.model_fields`` (recursing into each
sub-model) means the documentation can never silently drift from the code.

Usage:
    python scripts/gen_config_table.py            # print the Markdown table
    python scripts/gen_config_table.py -o out.md  # write the table to a file
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Iterator, List, Tuple, Union, get_args, get_origin

# Add the src/ directory to the path so the package imports without an install.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from netops_mcp.config.models import Config  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from pydantic_core import PydanticUndefined  # noqa: E402

# Environment variables the code / startup script actually read. Only these
# override configuration; every other setting is JSON-config-only. HTTP_HOST /
# HTTP_PORT / HTTP_PATH are forwarded by start_http_server.sh as
# --host / --port / --path CLI flags into ServerConfig.
CONFIG_ENV_OVERRIDES = {
    "server.host": "HTTP_HOST",
    "server.port": "HTTP_PORT",
    "server.path": "HTTP_PATH",
}

# Process-level environment variables that are NOT config-model fields but are
# read by the server / container runtime. Listed so the env surface is complete.
PROCESS_ENV_VARS: List[Tuple[str, str, str, str]] = [
    (
        "NETOPS_MCP_CONFIG",
        "str (path)",
        "config/config.json",
        "Path to the JSON config file loaded at startup (used when --config is omitted).",
    ),
    (
        "PYTHONUNBUFFERED",
        "str",
        "1",
        "Line-buffered stdout/stderr for container logs.",
    ),
]

# Human-readable effect for each dotted config key. Rows are still emitted for
# any field missing here (with a blank effect), so a newly added model field
# surfaces in the table automatically -- that is the drift guard working.
EFFECTS = {
    "logging.level": "Log verbosity (DEBUG / INFO / WARNING / ERROR).",
    "logging.format": "Python logging format string.",
    "logging.file": "Log file path (None = console only).",
    "security.allow_privileged_commands": (
        "Enable privileged scans (nmap -sS/-O); default off returns " "'disabled by config'."
    ),
    "security.allow_loopback": "Allow requests to loopback addresses (127.0.0.0/8, ::1).",
    "security.allow_link_local": "Allow link-local addresses (169.254.0.0/16, fe80::/10).",
    "security.allow_private": "Allow private / LAN address ranges (RFC 1918).",
    "security.block_metadata": ("Block cloud metadata endpoints (169.254.169.254, fd00:ec2::254)."),
    "security.allowed_hosts": "TrustedHost allow-list for the HTTP server (empty = all).",
    "security.rate_limit_requests": "Max requests per window per client.",
    "security.rate_limit_window": "Rate-limit window in seconds.",
    "security.require_auth": (
        "Require an API key for HTTP mode; without one the server fails fast at startup."
    ),
    "security.api_keys": "Accepted API keys as 'sha256:<64-hex>' digests only.",
    "security.enable_cors": "Enable the CORS middleware.",
    "security.cors_origins": (
        "Explicit allowed origins (wildcard '*' plus credentials is rejected at load)."
    ),
    "security.cors_allow_credentials": "Send Access-Control-Allow-Credentials.",
    "network.default_timeout": "Default per-command timeout (seconds).",
    "network.max_retries": "Max retries for retryable operations.",
    "network.ping_count": "Default ping packet count.",
    "network.traceroute_max_hops": "Default traceroute max hops.",
    "network.nmap_scan_timeout": "Default nmap scan timeout (seconds).",
    "network.max_scan_timeout": "Upper bound for scan timeouts (seconds).",
    "network.allowed_ports": "Permitted port-range specification.",
    "server.host": "HTTP bind address.",
    "server.port": "HTTP listen port.",
    "server.path": "MCP endpoint path.",
    "custom_settings": "Free-form user settings (not validated).",
}


def _type_name(annotation: Any) -> str:
    """Return a compact, readable name for a type annotation."""
    origin = get_origin(annotation)
    if origin is None:
        return getattr(annotation, "__name__", str(annotation).replace("typing.", ""))
    args = get_args(annotation)
    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        inner = ", ".join(_type_name(a) for a in non_none)
        if len(non_none) < len(args):
            return f"Optional[{inner}]"
        return f"Union[{inner}]"
    origin_name = getattr(origin, "__name__", str(origin))
    inner = ", ".join(_type_name(a) for a in args)
    return f"{origin_name}[{inner}]"


def _get_default(field: Any) -> Any:
    """Resolve a field's default value, invoking any default_factory."""
    if field.default_factory is not None:
        return field.default_factory()
    if field.default is not PydanticUndefined:
        return field.default
    return None


def _format_default(value: Any) -> str:
    """Format a default value as a Markdown code span."""
    if value is None:
        return "`None`"
    if isinstance(value, str):
        return f'`"{value}"`'
    return f"`{value!r}`"


def _iter_fields(model: type, prefix: str = "") -> Iterator[Tuple[str, Any, Any]]:
    """Yield (dotted-key, annotation, default) for every leaf config field."""
    for name, field in model.model_fields.items():
        annotation = field.annotation
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            yield from _iter_fields(annotation, prefix=f"{prefix}{name}.")
        else:
            yield f"{prefix}{name}", annotation, _get_default(field)


def build_table() -> str:
    """Build the full Markdown config/env reference table from the models."""
    rows = [
        "| Key | Type | Default | Env override | Effect |",
        "| --- | --- | --- | --- | --- |",
    ]
    for key, annotation, default in _iter_fields(Config):
        env = CONFIG_ENV_OVERRIDES.get(key, "")
        env_cell = f"`{env}`" if env else ""
        effect = EFFECTS.get(key, "")
        rows.append(
            f"| `{key}` | `{_type_name(annotation)}` | {_format_default(default)} "
            f"| {env_cell} | {effect} |"
        )
    for name, type_str, default, effect in PROCESS_ENV_VARS:
        rows.append(f"| — | `{type_str}` | `{default}` | `{name}` | {effect} |")
    return "\n".join(rows)


def main() -> None:
    """Print or write the model-derived config/env reference table."""
    parser = argparse.ArgumentParser(
        description="Generate the NetOps MCP config/env reference table from the Pydantic models."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Write the table to this file instead of stdout.",
    )
    args = parser.parse_args()

    table = build_table()
    if args.output:
        Path(args.output).write_text(table + "\n", encoding="utf-8")
    else:
        print(table)


if __name__ == "__main__":
    main()
