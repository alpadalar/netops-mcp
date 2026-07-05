# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-05

First public release of NetOpsMCP — a Python/FastMCP-based network operations
MCP server exposing 26 tools (ping, traceroute, mtr, nmap, DNS queries, HTTP
requests, and system monitoring) over both stdio and HTTP transports.

The `Changed` entries below describe **breaking changes relative to the
pre-release internal behavior**. If you ran an earlier internal build in HTTP
mode, read them before upgrading. Pre-1.0 history is intentionally not
backfilled.

### Added

- 26 network and system diagnostic tools grouped by domain: connectivity
  (ping, traceroute, mtr, telnet, netcat), DNS (nslookup, dig, host), HTTP
  (curl, httpie, api_test), discovery/scanning (nmap_scan, service_discovery,
  port_scan, service_enumeration), network state (ss, netstat, arp, arping),
  and system monitoring (system_status, cpu_usage, memory_usage, disk_usage,
  process_list, check_required_tools).
- Two transport modes sharing identical tool implementations: a stdio server
  (`netops-mcp` / `python -m netops_mcp.server`) and an HTTP server
  (`python -m netops_mcp.server_http`, path `/netops-mcp`, port `8815`).
- HTTP middleware stack: API-key authentication, per-client sliding-window
  rate limiting, Prometheus-format metrics at `/metrics`, CORS, and trusted-host
  handling, plus a `/health` endpoint.
- Pydantic-validated configuration (`logging`, `security`, `network`, `server`
  sections) loaded from JSON via `NETOPS_MCP_CONFIG`, with `extra='forbid'` so
  unknown keys are rejected.
- `scripts/generate_api_key.py` for generating API keys and their `sha256:`
  digests.

### Changed

- **BREAKING:** HTTP mode now requires an API key by default
  (`security.require_auth` defaults to `true`). Existing HTTP clients must
  configure an API key before the server will start; stdio mode is
  unaffected. Opt out explicitly with `"require_auth": false` (not
  recommended).
- **BREAKING:** `security.api_keys` accepts only `sha256:<64-hex>` digests;
  plain keys are rejected at config load time. Hash an existing key with
  `python -c "import hashlib;print('sha256:'+hashlib.sha256(b'YOUR-KEY').hexdigest())"`
  or regenerate with `python scripts/generate_api_key.py --hash`.
- Starting the HTTP server with authentication enabled but no API keys
  configured now fails fast before the port binds, printing a freshly
  generated example key, its paste-ready `sha256:` digest, and the explicit
  opt-out. The example key is never activated automatically.
- Configuration precedence is CLI flags > `config.server` > builtin defaults
  (`0.0.0.0` / `8815` / `/netops-mcp`).
- CORS `allow_credentials` is now bound to the
  `security.cors_allow_credentials` config field (default `false`) instead
  of being hardcoded to `true`.
- Configurations combining wildcard CORS origins (`"*"`) with
  `cors_allow_credentials: true` are rejected at config load time.

### Security

- SSRF protection resolves host/URL inputs and then classifies the resolved IP
  ("resolve-then-classify"): private/LAN addresses are allowed by default while
  loopback and link-local ranges — including the cloud metadata endpoints
  (`169.254.169.254`, `fd00:ec2::254`) — are blocked (`block_metadata=True`).
- The `curl`/`api_test` path pins the resolved IP with `curl --resolve`,
  closing the DNS-rebind window for HTTP requests. The `httpie` path cannot be
  IP-pinned and is documented as a residual in `SECURITY.md` — prefer `curl`
  for untrusted targets.
- DNS-rebind on `nmap` scan targets is closed.
- Privileged raw-socket scans (`nmap -sS` / `-O`) are gated behind
  `allow_privileged_commands` (default `false`), which returns an explicit
  "disabled by config" response rather than attempting the scan.
- API keys are compared in constant time and are only ever persisted as
  `sha256:` digests; plaintext keys never touch disk.

[0.1.0]: https://github.com/alpadalar/NetOpsMCP/releases/tag/v0.1.0
