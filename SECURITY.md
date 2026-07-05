# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please send an email to alp.adalar@gmail.com. All security vulnerabilities will be promptly addressed.

**Please do not report security vulnerabilities through public GitHub issues.**

### What to Include

When reporting a vulnerability, please include:

- Type of vulnerability
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

## Threat Model

NetOpsMCP wraps operating-system network utilities (`ping`, `traceroute`, `mtr`,
`nmap`, `curl`, `httpie`, DNS tools, and more) and exposes them as MCP tools. Because
every tool ultimately issues a real network probe from the host it runs on, the
central question is: **what can this server do to a network, what does it block by
default, and what must an operator explicitly opt into?** This section answers that
honestly and reflects the frozen, shipped behavior of the code — nothing here is
aspirational or "not yet implemented."

### What the server can do

- Send diagnostic probes (ICMP/UDP/TCP) to hosts you target: `ping`, `traceroute`, `mtr`, `telnet`, `netcat`, `arping`.
- Resolve DNS and issue HTTP(S) requests (`curl`, `httpie`, `api_test`).
- Scan ports and enumerate services with `nmap` (connect scans by default).
- Read local system state (CPU, memory, disk, processes, sockets) via `psutil`.

### What is blocked by default

**SSRF policy (resolve-then-classify).**
Before any HTTP request or scan runs, the target hostname is resolved with
`getaddrinfo` and every resulting IP is classified with the `ipaddress` module — a
**resolve-then-classify** approach that normalizes obfuscated encodings (decimal
`2130706433`, hex `0x7f000001`, octal, IPv6, `::ffff:`-mapped) before the policy
decision. By default:

- **Loopback** (`127.0.0.0/8`, `::1`) is **blocked** (`allow_loopback=false`).
- **Link-local**, including the cloud-metadata endpoints `169.254.169.254` and
  `fd00:ec2::254`, is **blocked** (`allow_link_local=false`, `block_metadata=true`).
- **Private / LAN** ranges are **allowed** (`allow_private=true`) — diagnosing hosts
  on your own network is the core purpose of the tool.
- **Reserved** ranges are always blocked; **global** addresses are allowed.

For HTTP tools the classified IP is **pinned into curl via `--resolve host:port:ip`**
and redirects are disabled (`--max-redirs 0`, never `-L`), so the address that was
classified is the exact address that is contacted. This closes the DNS-rebind /
TOCTOU window and redirect-to-metadata. Non-HTTP tools fail **open** on an
unresolvable host (a down host is a legitimate diagnostic target); HTTP tools fail
**closed** (an unresolvable host raises rather than running curl unpinned).

**Privileged nmap scan types.** `nmap` SYN/OS-detection scans (`quick` = `-sS`,
`full` = `-sS -sV -O`) are gated behind `security.allow_privileged_commands`
(default `false`) and return an explicit "disabled by config" error. Connect scans
(`-sT`) and version/script scans (`-sV -sC`) need no privilege and are always
available — they are the recommended default for unprivileged deployments.

**Command injection.** All tool inputs pass through central validators
(hostname / IP / port / URL) with argument sanitization; commands are built as argv
lists (no `shell=True` string interpolation).

**Shared-file races.** `curl_request` and `api_test` write to a per-request
`tempfile.mkstemp` (mode `0600`) that is unlinked in a `finally` block — there is no
shared `/tmp` output path to race or symlink-clobber.

### The two-layer privileged model (NET_RAW vs allow_privileged_commands)

Privileged network operations are a deliberate **two-step opt-in**, and the two
layers are independent:

| Layer | Governs | Where | Default |
|-------|---------|-------|---------|
| **OS: Docker `NET_RAW`** (+ `NET_ADMIN`) capability | Raw-socket diagnostics — `ping`, `arping`, and nmap raw-packet modes need it to open raw sockets at all | container runtime (`docker-compose.yml` `cap_add`) | granted (basic diagnostics work out of the box) |
| **App: `security.allow_privileged_commands`** | nmap privileged scan types only — `quick` (`-sS`) and `full` (`-sS -sV -O`) | `SecurityConfig`, read by `nmap_scan` | `false` (denied) |

- `ping` / `arping` ride the **NET_RAW** layer and are **never** gated by the config flag — raw-socket diagnostics are the core tool value.
- nmap `-sS` / `-O` require **both** the OS capability **and** the config flag set to `true`. Setting `allow_privileged_commands=true` without `NET_RAW` still fails at the OS layer, so the flag is a fail-safe app-layer denial that does not, by itself, grant capability. Removing `NET_RAW` breaks `ping` / `arping` too.
- Connect (`-sT`) and version/script (`-sV -sC`) scans need neither and are always available.

### Authentication model

- **HTTP transport:** API keys are stored only as **sha256** digests
  (`sha256:<64-hex>`); the plaintext key is never persisted. Incoming keys are
  hashed and compared in **constant-time** (`hmac.compare_digest`), accepted via
  `Authorization: Bearer`, `X-API-Key`, or `API-Key` headers. Authentication is
  **required by default** (`require_auth=true`), and the server **fails fast at
  startup** if `require_auth` is on but no keys are configured — it never
  fail-opens. sha256 is appropriate here because API keys are high-entropy random
  tokens, not user passwords.
- **stdio transport:** no authentication — it is a local, single-user transport
  (the client launches the server as a subprocess), so network auth does not apply.

### Documented residuals

- **httpie cannot be IP-pinned.** `httpie_request` classifies the target host with
  the same SSRF policy, but `httpie` has no `curl --resolve` equivalent, so its DNS
  lookup is not pinned — a small DNS-rebind window remains between classification and
  fetch. **Use `curl_request` / `api_test` for untrusted URLs**; they are the
  fully-pinned, SSRF-safe HTTP path. This is an accepted architectural residual.
- **nmap DNS-rebind is CLOSED.** Scan targets are classified and the resolved IP is
  used, so the plain-hostname DNS-rebind vector documented in earlier phases is
  fixed, not residual.

## Security Best Practices

### Authentication

1. **API Keys**: Always use strong, randomly generated API keys
   - Use the provided script: `python scripts/generate_api_key.py`
   - Never commit API keys to version control
   - Rotate API keys regularly

2. **Environment Variables**: Store sensitive data in environment variables, not in config files
   - Use `env.production.example` as a template
   - Never commit `.env` files

3. **HTTPS**: Always use HTTPS in production
   - Use a reverse proxy (nginx, Caddy) with SSL/TLS
   - Never expose the application directly to the internet

### Network Security

1. **Firewall Rules**: Configure appropriate firewall rules
   - Only allow necessary ports (8815 or your custom port)
   - Restrict access by IP address when possible

2. **Rate Limiting**: Configure appropriate rate limits
   - Default: 100 requests per 60 seconds
   - Adjust based on your use case

3. **Network Scanning**: Be aware of legal implications
   - **Only scan systems (hosts, networks, and ports) you own or have explicit written permission to test.**
   - Some network scanning activities may be illegal in your jurisdiction

### Docker Security

1. **Non-Root User**: The application runs as a non-root user
   - User ID: 1000 (netopsmcp)
   - Limited privileges

2. **Capabilities**: Only required capabilities are granted
   - `NET_ADMIN`: For network configuration
   - `NET_RAW`: For raw packet operations (ping, traceroute)

3. **Resource Limits**: Set appropriate resource limits
   - CPU: 2 cores maximum
   - Memory: 1GB maximum

4. **Image Scanning**: Regularly scan Docker images
   - Use Trivy or similar tools
   - Update base images regularly

### Input Validation

All user inputs are validated to prevent:
- Command injection attacks
- Path traversal attacks
- Invalid network parameters
- Malformed URLs and domains

### Logging and Monitoring

1. **Structured Logging**: All requests and errors are logged
   - Review logs regularly
   - Monitor for suspicious activity

2. **Metrics**: Monitor application metrics
   - Request rates
   - Error rates
   - Authentication failures

3. **Alerts**: Set up alerts for:
   - High error rates
   - Authentication failures
   - Rate limit violations

## Known Security Considerations

### Privileged Network Operations

Some network diagnostic tools require elevated privileges:
- **ping**: Requires `CAP_NET_RAW` capability
- **traceroute**: Requires `CAP_NET_RAW` capability
- **nmap**: SYN/OS-detection scans (`-sS` / `-O`) additionally require `security.allow_privileged_commands=true` (default `false`); connect scans (`-sT`) do not
- **arping**: Requires `CAP_NET_RAW` capability

**Mitigation**: The Docker container runs with only the minimal required capabilities (`NET_ADMIN`, `NET_RAW`) instead of full privileged mode, and privileged nmap scan types are additionally gated in the app by config (`allow_privileged_commands`, default off). See the [two-layer privileged model](#the-two-layer-privileged-model-net_raw-vs-allow_privileged_commands) in the Threat Model.

### Network Scanning Legal Issues

Network scanning tools can be used for malicious purposes:
- Port scanning may be interpreted as hostile activity
- Some jurisdictions have laws against unauthorized network scanning
- ISPs may have acceptable use policies that prohibit scanning

**Mitigation**:
- Document and communicate intended use
- **Only scan systems (hosts, networks, and ports) you own or have explicit written permission to test.**
- Implement logging and audit trails

### Command Execution

The application executes system commands:
- All inputs are validated and sanitized
- Command injection patterns are detected and blocked
- Commands run with limited user privileges

**Mitigation**: Input validation is implemented at multiple layers.

## Security Updates

### Automated Scanning

- **GitHub Actions**: Automated security scanning on every push
- **Trivy**: Container image vulnerability scanning
- **Bandit**: Python security linter
- **Safety**: Dependency vulnerability checking

### Manual Updates

Check for security updates regularly:

```bash
# Update dependencies
uv pip list --outdated

# Security audit
safety check

# Scan for vulnerabilities
bandit -r src/
```

## Secure Deployment Checklist

- [ ] Enable authentication (`require_auth: true`)
- [ ] Generate and configure strong API keys
- [ ] Use environment variables for secrets
- [ ] Configure HTTPS/TLS with reverse proxy
- [ ] Set up firewall rules
- [ ] Configure rate limiting
- [ ] Enable CORS only for trusted origins
- [ ] Set resource limits
- [ ] Configure logging and monitoring
- [ ] Regular security updates
- [ ] Regular log review
- [ ] Backup configuration and logs

## Contact

For security concerns, please contact:
- Email: alp.adalar@gmail.com
- GitHub: @alpadalar

## Attribution

This security policy is based on industry best practices and adapted for NetOps MCP.







