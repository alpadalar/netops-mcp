# NetOps MCP

[![Tests](https://img.shields.io/github/actions/workflow/status/alpadalar/NetOpsMCP/test.yml?label=tests)](https://github.com/alpadalar/NetOpsMCP/actions/workflows/test.yml)
[![Lint](https://img.shields.io/github/actions/workflow/status/alpadalar/NetOpsMCP/lint.yml?label=lint)](https://github.com/alpadalar/NetOpsMCP/actions/workflows/lint.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A [Model Context Protocol](https://modelcontextprotocol.io) server that exposes
26 network and system diagnostic tools — `ping`, `traceroute`, `mtr`, `nmap`,
DNS queries, HTTP requests, and system monitoring — to MCP clients such as
Claude Desktop, Claude Code, and Cursor. Each tool is a thin, input-validated
wrapper around a standard OS utility. Two transports are supported: **stdio**
(the client launches the server as a subprocess) and **HTTP** (a long-running
server with auth, rate limiting, and metrics).

## Features

- **Connectivity** — `ping`, `traceroute`, `mtr`, `telnet`, `netcat`
- **DNS** — `nslookup`, `dig`, `host`
- **HTTP / API** — `curl`, `httpie`, `api_test`
- **Discovery & scanning** — `nmap_scan`, `service_discovery`, `port_scan`, `service_enumeration`
- **Network state** — `ss`, `netstat`, `arp`, `arping`
- **System monitoring** — status, CPU, memory, disk, process list, tool availability

## Requirements

- **Python >= 3.10** and [uv](https://github.com/astral-sh/uv) (recommended)
- **Linux or macOS** — the network tools are OS-specific; Windows is not supported
- **System tools** on `PATH` (availability is checked at startup):
  `curl`, `ping`, `traceroute`, `mtr`, `telnet`, `nc`, `nmap`, `ss`, `netstat`,
  `arp`, `arping`, `nslookup`, `dig`, `host`. `httpie` is optional.

## Installation

```bash
git clone https://github.com/alpadalar/NetOpsMCP.git
cd NetOpsMCP

# Using uv (recommended)
uv venv
source .venv/bin/activate
uv pip install -e .
```

<details>
<summary>Alternatives (pip, Docker)</summary>

```bash
# pip
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Docker (HTTP mode) — see Authentication before first run
docker compose up -d
```
</details>

## Quick Start

### stdio (no auth)

```bash
uv run netops-mcp          # or: python -m netops_mcp.server
```

Point an MCP client at this command (see below).

### HTTP

HTTP mode **requires an API key by default** and refuses to start without one —
see [Authentication](#authentication). Once a key is configured:

```bash
# Pass the config that holds your API key — without it the server loads
# built-in defaults (require_auth: true, no keys) and fails fast.
python -m netops_mcp.server_http --config config/config.json --host 0.0.0.0 --port 8815
# or: NETOPS_MCP_CONFIG=config/config.json python -m netops_mcp.server_http
# or: ./start_http_server.sh   (defaults to config/config.json)

curl http://localhost:8815/health          # health check (no key required)
```

## Authentication

> **Breaking change (0.1.0):** HTTP mode now requires an API key by default
> (`security.require_auth` defaults to `true`). stdio mode is unaffected (local
> transport, no auth).

On a fresh checkout the HTTP server **fails fast before binding the port** when
no key is configured, printing copy-paste setup instructions plus a freshly
generated example key (never activated automatically).

**1. Generate a key.** The plain key is printed once (never stored);
`--config` writes only its `sha256:` digest and enables `require_auth`:

```bash
python scripts/generate_api_key.py                             # print a plain key
python scripts/generate_api_key.py -n 2 --config config/config.json   # write digests
```

Flags: `-n/--count`, `-l/--length` (default 32), `--hash`, `--json`,
`--config PATH`. To hash an existing key:
`python -c "import hashlib;print('sha256:'+hashlib.sha256(b'YOUR-KEY').hexdigest())"`.

**2. Configure.** Only `sha256:<64-hex>` digests are accepted — plain keys are
rejected at config load time:

```json
{ "security": { "require_auth": true, "api_keys": ["sha256:<hex-digest-of-your-key>"] } }
```

**3. Authenticate.** Clients send the **plain** key (the server stores and
compares only the digest, in constant time). Any of three headers works:

```bash
curl -H "Authorization: Bearer YOUR-KEY" http://localhost:8815/netops-mcp
curl -H "X-API-Key: YOUR-KEY"            http://localhost:8815/netops-mcp
curl -H "API-Key: YOUR-KEY"              http://localhost:8815/netops-mcp
```

A keyless request returns `401`; an invalid key returns `403`. `/health` is
always public; `/metrics` requires the key while auth is enabled (it is only
public when `require_auth: false`).

**Opt out** (only on trusted, isolated networks):

```json
{ "security": { "require_auth": false } }
```

Host/port/path resolve as **CLI flags > config `server` section > built-in
defaults** (`0.0.0.0` / `8815` / `/netops-mcp`). `--config` falls back to
`$NETOPS_MCP_CONFIG` when omitted.

## Configuration

Configuration is loaded from a JSON file (`config/config.json` by default, or
`$NETOPS_MCP_CONFIG`) and validated by Pydantic models. Copy the fully
documented [`config/config.example.json`](config/config.example.json) to get
started. Only five environment variables are read; everything else lives in the
JSON file.

| Env var | Effect |
| --- | --- |
| `HTTP_HOST` / `HTTP_PORT` / `HTTP_PATH` | Forwarded by `start_http_server.sh` as `--host` / `--port` / `--path` |
| `NETOPS_MCP_CONFIG` | Path to the JSON config file (used when `--config` is omitted) |
| `PYTHONUNBUFFERED` | Line-buffered stdout for container logs |

Most-used config keys (the full model-derived table is regenerable with
`python scripts/gen_config_table.py`):

| Key | Default | Effect |
| --- | --- | --- |
| `security.require_auth` | `true` | Require an API key for HTTP mode; fails fast at startup without one |
| `security.api_keys` | `[]` | Accepted keys as `sha256:<64-hex>` digests only |
| `security.allow_privileged_commands` | `false` | Enable privileged nmap scans (`-sS` / `-O`); off returns "disabled by config" |
| `security.rate_limit_requests` / `_window` | `100` / `60` | Sliding-window rate limit per client (requests / seconds) |
| `security.enable_cors` | `false` | Enable CORS (wildcard origin + credentials is rejected at load) |
| `network.max_scan_timeout` | `300` | Upper bound for scan timeouts (seconds) |
| `server.host` / `port` / `path` | `0.0.0.0` / `8815` / `/netops-mcp` | HTTP bind address, port, and MCP endpoint path |

## MCP Client Configuration

### stdio (Claude Desktop / Cursor)

Add to `claude_desktop_config.json` (Claude Desktop) or `.cursor/mcp.json`
(Cursor):

```json
{
  "mcpServers": {
    "netops-mcp": {
      "command": "uv",
      "args": ["run", "netops-mcp"],
      "cwd": "/absolute/path/to/NetOpsMCP"
    }
  }
}
```

Claude Code adds the same server with one command:

```bash
claude mcp add netops-mcp -- uv run netops-mcp
```

### HTTP + API key

Point a client at a running HTTP server, sending the plain key as a header
(`.mcp.json` / `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "netops-mcp": {
      "type": "http",
      "url": "http://localhost:8815/netops-mcp",
      "headers": { "X-API-Key": "YOUR-KEY" }
    }
  }
}
```

Claude Code can add the same in one command:
`claude mcp add --transport http netops-mcp http://localhost:8815/netops-mcp --header "X-API-Key: YOUR-KEY"`.

## Security

Inputs are validated to prevent command injection, and HTTP/scan targets are
resolved then classified so requests to loopback, link-local, and cloud
metadata addresses are blocked by default (private/LAN ranges are allowed).
Privileged nmap scans are gated behind config. In production, run HTTP mode
behind a reverse proxy (nginx, Caddy) for TLS — never expose the plain HTTP port
to the internet. The Docker image runs as a non-root user with only `NET_ADMIN`
+ `NET_RAW` capabilities and 2 CPU / 1 GB limits (`docker-compose.yml`).

> **Responsible use.** The scanning tools (`nmap_scan`, `port_scan`,
> `service_enumeration`) and other active probes may be **illegal without
> authorization**. Only scan hosts and networks you own or have explicit
> permission to test. You are solely responsible for your use of these tools.

See [SECURITY.md](SECURITY.md) for the full threat model and the vulnerability
disclosure process.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup,
the test mocking strategy, and PR guidelines. By participating you agree to the
[Code of Conduct](CODE_OF_CONDUCT.md).

## License

MIT — see [LICENSE](LICENSE).

## Hosted deployment

A hosted deployment is available on [Fronteir AI](https://fronteir.ai/mcp/alpadalar-netops-mcp).
