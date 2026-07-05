# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Email **alp.adalar@gmail.com** with:

- The type of vulnerability and its impact (how an attacker might exploit it).
- Affected source file(s) and the tag/branch/commit.
- Any configuration required to reproduce, plus step-by-step instructions and a
  proof-of-concept if possible.

All reports are reviewed and addressed promptly.

## Threat Model

NetOpsMCP wraps OS network utilities (`ping`, `traceroute`, `mtr`, `nmap`,
`curl`, `httpie`, DNS tools, and more) and exposes them as MCP tools. Because
every tool issues a real network probe from the host it runs on, the central
questions are: **what can the server do to a network, what does it block by
default, and what must an operator explicitly opt into?** Everything below
reflects the shipped behavior of the code.

### What the server can do

- Send diagnostic probes (ICMP/UDP/TCP): `ping`, `traceroute`, `mtr`, `telnet`,
  `netcat`, `arping`.
- Resolve DNS and issue HTTP(S) requests (`curl`, `httpie`, `api_test`).
- Scan ports and enumerate services with `nmap` (connect scans by default).
- Read local system state (CPU, memory, disk, processes, sockets) via `psutil`.

### What is blocked by default

**SSRF policy (resolve-then-classify).** Before any HTTP request or scan runs,
the target hostname is resolved with `getaddrinfo` and every resulting IP is
classified with the `ipaddress` module — normalizing obfuscated encodings
(decimal `2130706433`, hex `0x7f000001`, octal, IPv6, `::ffff:`-mapped) before
the policy decision:

- **Loopback** (`127.0.0.0/8`, `::1`) is **blocked** (`allow_loopback=false`).
- **Link-local**, including cloud-metadata endpoints `169.254.169.254` and
  `fd00:ec2::254`, is **blocked** (`allow_link_local=false`, `block_metadata=true`).
- **Private / LAN** ranges are **allowed** (`allow_private=true`) — diagnosing
  your own network is the core purpose of the tool.
- **Reserved** ranges are always blocked; **global** addresses are allowed.

For HTTP tools the classified IP is **pinned into curl via `--resolve`** and
redirects are disabled (`--max-redirs 0`, never `-L`), so the address that was
classified is the exact address contacted — closing the DNS-rebind / TOCTOU
window and redirect-to-metadata. Non-HTTP tools fail **open** on an unresolvable
host (a down host is a legitimate diagnostic target); HTTP tools fail **closed**.

**Command injection.** All tool inputs pass through central validators
(hostname / IP / port / URL) with argument sanitization; commands are built as
argv lists (no `shell=True` string interpolation).

**Shared-file races.** `curl_request` and `api_test` write to a per-request
`tempfile.mkstemp` (mode `0600`) unlinked in a `finally` block — no shared
`/tmp` path to race or symlink-clobber.

### The two-layer privileged model (NET_RAW vs allow_privileged_commands)

Privileged network operations are a deliberate **two-step opt-in**, and the two
layers are independent:

| Layer | Governs | Where | Default |
|-------|---------|-------|---------|
| **OS: Docker `NET_RAW`** (+ `NET_ADMIN`) | Raw-socket diagnostics — `ping`, `arping`, nmap raw-packet modes need it to open raw sockets at all | container runtime (`docker-compose.yml` `cap_add`) | granted |
| **App: `security.allow_privileged_commands`** | nmap privileged scan types only — `quick` (`-sS`) and `full` (`-sS -sV -O`) | `SecurityConfig`, read by `nmap_scan` | `false` (denied) |

- `ping` / `arping` ride the **NET_RAW** layer and are **never** gated by the
  config flag — raw-socket diagnostics are the core tool value.
- nmap `-sS` / `-O` require **both** the OS capability **and** the config flag.
  Setting `allow_privileged_commands=true` without `NET_RAW` still fails at the
  OS layer; removing `NET_RAW` breaks `ping` / `arping` too.
- Connect (`-sT`) and version/script (`-sV -sC`) scans need neither and are
  always available — the recommended default for unprivileged deployments.

### Authentication model

- **HTTP transport:** API keys are stored only as **sha256** digests
  (`sha256:<64-hex>`); the plaintext key is never persisted. Incoming keys are
  hashed and compared in **constant time** (`hmac.compare_digest`), accepted via
  `Authorization: Bearer`, `X-API-Key`, or `API-Key` headers. Authentication is
  **required by default** (`require_auth=true`), and the server **fails fast at
  startup** if `require_auth` is on but no keys are configured — it never
  fail-opens. sha256 is appropriate here because API keys are high-entropy random
  tokens, not user passwords.
- **stdio transport:** no authentication — it is a local, single-user transport,
  so network auth does not apply.

### Documented residuals

- **httpie cannot be IP-pinned.** `httpie_request` classifies the target with the
  same SSRF policy, but `httpie` has no `curl --resolve` equivalent, so a small
  DNS-rebind window remains between classification and fetch. **Use
  `curl_request` / `api_test` for untrusted URLs** — they are the fully-pinned,
  SSRF-safe HTTP path. This is an accepted architectural residual.
- **nmap DNS-rebind is CLOSED** — scan targets are classified and the resolved IP
  is used; the plain-hostname rebind vector is fixed, not residual.
- **Dependency scanning is advisory.** `pip-audit` runs in CI but does not block
  merges; review its findings when updating dependencies.

## Best Practices

- **Enable auth** (`require_auth: true`, the default) and use strong,
  randomly-generated keys (`python scripts/generate_api_key.py`). Never commit
  keys; rotate them regularly.
- **Always use HTTPS in production** via a reverse proxy (nginx, Caddy). Never
  expose the plain HTTP port directly to the internet.
- **Restrict the network** — firewall to the necessary port only; run in isolated
  environments where possible; tune `rate_limit_requests` / `rate_limit_window`.
- **Enable CORS only for trusted origins** (wildcard `*` + credentials is
  rejected at config load).
- **Only scan hosts, networks, and ports you own or have explicit written
  permission to test** — unauthorized scanning may be illegal in your
  jurisdiction and may violate ISP acceptable-use policies.

## Automated Scanning

CI runs security tooling on every push: **Bandit** (Python linter), **Trivy**
(container image scanning), and **pip-audit** (dependency advisories). Run them
locally with:

```bash
bandit -r src/
pip-audit
```
