# NetOps MCP - Network Operations Tools MCP Server

A comprehensive Model Context Protocol (MCP) server that provides access to essential network operations and infrastructure tools through a standardized interface.

## 🚀 Features

### Network Connectivity Tools
- **Ping**: Test host connectivity with customizable packet count and timeout
- **Traceroute**: Trace network path with configurable max hops
- **MTR**: Monitor network path with real-time statistics
- **Telnet**: Test port connectivity using telnet
- **Netcat**: Test port connectivity using netcat

### HTTP/API Testing Tools
- **cURL**: Execute HTTP requests with full control over headers, methods, and data
- **HTTPie**: Alternative HTTP client with simplified syntax
- **API Testing**: Validate API endpoints with expected status codes

### DNS Tools
- **nslookup**: Query DNS records with various record types
- **dig**: Advanced DNS querying tool
- **host**: Simple DNS lookup utility

### Network Discovery Tools
- **Nmap**: Network scanning and service enumeration
- **Port Scanning**: Targeted port scanning capabilities
- **Service Discovery**: Identify running services on targets

### System Monitoring Tools
- **SS**: Socket statistics and connection monitoring
- **Netstat**: Network statistics and connection information
- **ARP**: Address Resolution Protocol table management
- **ARPing**: Test ARP connectivity

### System Information Tools
- **System Status**: CPU, memory, and disk usage monitoring
- **Process List**: Running process enumeration
- **Required Tools Check**: Verify system tool availability

## 📋 Prerequisites

### Required System Tools
The following tools must be installed on the system:

```bash
# Network tools
curl, ping, traceroute, mtr, telnet, nc (netcat)

# DNS tools
nslookup, dig, host

# Network discovery
nmap

# System tools
ss, netstat, arp, arping

# HTTP tools
httpie (optional, for enhanced HTTP testing)
```

### Python Requirements
- Python 3.8+
- uv package manager (recommended)

## 🛠️ Installation

### Using uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/alpadalar/NetOpsMCP.git
cd NetOpsMCP

# Install dependencies using uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/alpadalar/NetOpsMCP.git
cd NetOpsMCP

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Using Docker

```bash
# Build and run with Docker Compose
docker compose up -d

# Or build manually
docker build -t netopsmcp .
docker run -p 8815:8815 netopsmcp
```

## 🚀 Quick Start

### 1. Start the Server

> **Note:** HTTP mode requires an API key by default. On a fresh checkout the
> server refuses to start and prints setup instructions — see
> [Authentication](#-authentication-breaking-change) below.

```bash
# Using Python directly
python -m netops_mcp.server_http --host 0.0.0.0 --port 8815

# Using Docker
docker compose up -d

# Using the provided script
./start_http_server.sh
```

### 2. Test the Server

```bash
# Health check
curl http://localhost:8815/health

# Test system requirements
curl -X POST http://localhost:8815/netops-mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "check_required_tools", "params": {}}'
```

### 3. Example Usage

```python
# Ping a host
result = ping_host("google.com", count=4, timeout=10)

# Test HTTP endpoint
result = curl_request("https://httpbin.org/get", method="GET")

# DNS lookup
result = nslookup_query("google.com", record_type="A")

# Network scan
result = nmap_scan("192.168.1.1", ports="1-1000", scan_type="basic")
```

## 🔐 Authentication (BREAKING CHANGE)

> **BREAKING CHANGE:** HTTP mode now requires an API key by default
> (`security.require_auth` defaults to `true`). Existing HTTP clients must
> configure an API key before the server will start. **stdio mode is
> unaffected.** To opt out explicitly, set `"require_auth": false` in the
> config file (NOT recommended).

> **⚠️ Known limitation (until Phase 3):** What is active today is the
> **fail-fast startup gate** — with `require_auth: true` and no key
> configured, the server refuses to start (see *First Run* below). **Per-request
> enforcement is not yet wired to the served endpoint:** the authentication,
> rate-limiting, and CORS middleware are not yet applied to the live HTTP app,
> so once a key is configured the server starts but does **not** currently
> reject keyless requests at runtime. Wiring the middleware to the served app
> (and the end-to-end tests that prove it) lands in **Phase 3 (REF-07)**. Until
> then, do **not** expose the HTTP endpoint on an untrusted network assuming
> requests are authenticated — run it only on a trusted/isolated network or
> behind an authenticating reverse proxy. stdio mode is unaffected.

### First Run

Starting the HTTP server with no API keys configured fails fast — the server
refuses to start *before* binding the port and exits with copy-paste
instructions:

```text
Error: HTTP mode requires an API key (require_auth is enabled by default).
  1. Example key (generated now, save it): <fresh-random-key>
  2. Add its hash to config security.api_keys: "sha256:<hex-digest-of-that-key>"
  3. Or explicitly opt out: "require_auth": false  (NOT recommended)
```

The example key is freshly generated on every failed start and is **never
activated automatically** — save it (or generate your own, below), add its
hash to the config, and restart.

### Generating an API Key

Use the bundled generator script:

```bash
# Generate one key; the plain key is printed ONCE and never stored
python scripts/generate_api_key.py

# Generate a key, show its sha256:<hex> digest, and write the digest
# into config/config.json (security.api_keys + require_auth: true)
python scripts/generate_api_key.py --hash --config config/config.json
```

Available flags: `-n/--count` (number of keys, default 1), `-l/--length`
(key length, default 32), `--hash` (also print the paste-ready
`sha256:<hex>` digest), `--json` (JSON output), `--config PATH` (append
digests to that config file and enable `require_auth`).

To hash an existing key yourself, use this one-liner:

```bash
python -c "import hashlib;print('sha256:'+hashlib.sha256(b'YOUR-KEY').hexdigest())"
```

### Config Format

Only `sha256:<64-hex>` digests are accepted in `security.api_keys` — plain
keys are rejected at config load time:

```json
{
  "security": {
    "require_auth": true,
    "api_keys": [
      "sha256:0f70dbbe4175927d0c7ff3bdc45622f13e6a5d306248731395a8995974effe25"
    ]
  }
}
```

(The digest above is an example — it is the hash of the literal string
`YOUR-KEY`. Use the digest of your own key.)

### Making Authenticated Requests

> **Note:** this is the request format clients will use once per-request
> enforcement is wired to the served endpoint in **Phase 3 (REF-07)** — see the
> *Known limitation* note above. Today the server does not yet reject keyless
> requests at runtime.

Clients send the **plain** key (not the digest); the server hashes it and
compares digests in constant time. Three header forms are accepted:

```bash
curl -H "Authorization: Bearer YOUR-KEY" http://localhost:8815/netops-mcp
curl -H "X-API-Key: YOUR-KEY" http://localhost:8815/netops-mcp
curl -H "API-Key: YOUR-KEY" http://localhost:8815/netops-mcp
```

`/health` and `/metrics` are exempt paths in the auth middleware (relevant once
the middleware is wired to the served app in Phase 3).

### Opting Out (NOT recommended)

```json
{
  "security": {
    "require_auth": false
  }
}
```

This disables authentication entirely for HTTP mode. Only use it on trusted,
isolated networks.

### Host / Port / Path Precedence

HTTP server settings resolve in this order (highest wins):

1. CLI flags — `--host`, `--port`, `--path`
2. Config file `server` section — `server.host`, `server.port`, `server.path`
3. Built-in defaults — `0.0.0.0`, `8815`, `/netops-mcp`

`--config` falls back to the `NETOPS_MCP_CONFIG` environment variable when
omitted. Note that `start_http_server.sh` always passes CLI flags (from
`HTTP_HOST`/`HTTP_PORT`/`HTTP_PATH` or its own defaults), so the config
file's `server` section takes effect when launching the module directly:
`python -m netops_mcp.server_http --config config/config.json`.

### CORS

CORS is disabled by default (`enable_cors: false`). When enabling it, list
explicit origins — wildcard origins combined with credentials are rejected
at config load time:

```json
{
  "security": {
    "enable_cors": true,
    "cors_origins": ["https://app.example.com"],
    "cors_allow_credentials": false
  }
}
```

`cors_allow_credentials` defaults to `false` and is passed straight to the
CORS middleware. Setting `cors_allow_credentials: true` while `cors_origins`
contains a wildcard (`"*"`) fails config validation.

## 📖 API Reference

### Network Connectivity

#### `ping_host(host: str, count: int = 4, timeout: int = 10)`
Test connectivity to a host using ping.

**Parameters:**
- `host`: Target hostname or IP address
- `count`: Number of ping packets (default: 4)
- `timeout`: Timeout in seconds (default: 10)

**Returns:** Ping statistics and results

#### `traceroute_path(target: str, max_hops: int = 30, timeout: int = 30)`
Trace network path to a target.

**Parameters:**
- `target`: Target hostname or IP address
- `max_hops`: Maximum number of hops (default: 30)
- `timeout`: Timeout in seconds (default: 30)

**Returns:** Network path information

#### `mtr_monitor(target: str, count: int = 10, timeout: int = 30)`
Monitor network path using MTR.

**Parameters:**
- `target`: Target hostname or IP address
- `count`: Number of probes (default: 10)
- `timeout`: Timeout in seconds (default: 30)

**Returns:** MTR statistics and hop information

### HTTP Testing

#### `curl_request(url: str, method: str = "GET", headers: dict = None, data: dict = None, timeout: int = 30)`
Execute HTTP request using curl.

**Parameters:**
- `url`: Target URL
- `method`: HTTP method (GET, POST, PUT, DELETE, PATCH)
- `headers`: HTTP headers dictionary
- `data`: Request data for POST/PUT requests
- `timeout`: Request timeout in seconds

**Returns:** HTTP response and timing information

#### `httpie_request(url: str, method: str = "GET", headers: dict = None, data: dict = None, timeout: int = 30)`
Execute HTTP request using HTTPie.

**Parameters:** Same as curl_request

**Returns:** HTTP response and timing information

### DNS Tools

#### `nslookup_query(domain: str, record_type: str = "A", server: str = None)`
Query DNS records using nslookup.

**Parameters:**
- `domain`: Target domain name
- `record_type`: DNS record type (A, AAAA, MX, NS, TXT, CNAME)
- `server`: Custom DNS server (optional)

**Returns:** DNS query results

#### `dig_query(domain: str, record_type: str = "A", server: str = None)`
Query DNS records using dig.

**Parameters:** Same as nslookup_query

**Returns:** Detailed DNS query results

### Network Discovery

#### `nmap_scan(target: str, ports: str = None, scan_type: str = "basic", timeout: int = 300)`
Scan network using nmap.

**Parameters:**
- `target`: Target hostname, IP, or network range
- `ports`: Port range (e.g., "1-1000", "80,443,8080")
- `scan_type`: Scan type (basic, full, stealth)
- `timeout`: Scan timeout in seconds

**Returns:** Network scan results

#### `port_scan(target: str, ports: str, timeout: int = 60)`
Perform targeted port scanning.

**Parameters:**
- `target`: Target hostname or IP address
- `ports`: Port range to scan
- `timeout`: Scan timeout in seconds

**Returns:** Port scan results

### System Monitoring

#### `system_status()`
Get system status information.

**Returns:** CPU, memory, and disk usage statistics

#### `ss_connections(state: str = None, protocol: str = None)`
Show network connections using ss.

**Parameters:**
- `state`: Filter by connection state
- `protocol`: Filter by protocol

**Returns:** Network connection information

#### `netstat_connections(state: str = None, protocol: str = None)`
Show network connections using netstat.

**Parameters:** Same as ss_connections

**Returns:** Network connection information

## 🧪 Testing

### Run All Tests

```bash
# Using pytest
pytest tests/ -v

# Using uv
uv run pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
```

### Test Categories

- **Unit Tests**: Individual tool functionality
- **Integration Tests**: End-to-end workflow testing
- **Mock Tests**: Command execution simulation
- **Validation Tests**: Input validation and error handling

### Test Coverage

The test suite covers:
- ✅ All tool methods and functionality
- ✅ Input validation and error handling
- ✅ Command execution and output parsing
- ✅ Edge cases and error scenarios
- ✅ Mock testing for external dependencies

To generate coverage reports:
```bash
# Generate HTML coverage report
pytest tests/ --cov=src --cov-report=html

# Generate terminal coverage report
pytest tests/ --cov=src --cov-report=term-missing

# Generate both reports
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
```

## 🔧 Configuration

### Environment Variables

```bash
# Server configuration
NETOPS_MCP_HOST=0.0.0.0
NETOPS_MCP_PORT=8815
NETOPS_MCP_LOG_LEVEL=INFO

# Tool timeouts
PING_TIMEOUT=10
TRACEROUTE_TIMEOUT=30
MTR_TIMEOUT=30
CURL_TIMEOUT=30
NMAP_TIMEOUT=300
```

### Configuration File

The server will automatically create a default configuration file from `config/config.example.json` on first run, or you can create `config/config.json` manually:

```json
{
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "logs/netops-mcp.log"
  },
  "security": {
    "allow_privileged_commands": false,
    "allowed_hosts": [],
    "rate_limit_requests": 100,
    "rate_limit_window": 60,
    "require_auth": true,
    "api_keys": [
      "sha256:0f70dbbe4175927d0c7ff3bdc45622f13e6a5d306248731395a8995974effe25"
    ]
  },
  "network": {
    "default_timeout": 30,
    "max_scan_timeout": 300,
    "allowed_ports": "1-65535"
  },
  "server": {
    "host": "0.0.0.0",
    "port": 8815,
    "path": "/netops-mcp"
  }
}
```

## 🐳 Docker Support

### Docker Compose

```yaml
version: '3.8'
services:
  netopsmcp:
    build: .
    ports:
      - "8815:8815"
    environment:
      - NETOPS_MCP_HOST=0.0.0.0
      - NETOPS_MCP_PORT=8815
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8815/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Docker Build

```bash
# Build image
docker build -t netopsmcp .

# Run container
docker run -d \
  --name netopsmcp \
  -p 8815:8815 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config:/app/config \
  netopsmcp
```

## 📊 Monitoring and Logging

### Log Levels

- **DEBUG**: Detailed debugging information
- **INFO**: General operational messages
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for failed operations

### Log Files

- `logs/netops-mcp.log`: Main application log
- `logs/access.log`: HTTP access log
- `logs/error.log`: Error log

### Health Checks

```bash
# Check server health
curl http://localhost:8815/health

# Check system requirements
curl -X POST http://localhost:8815/netops-mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "check_required_tools", "params": {}}'
```

## 🔒 Security Considerations

### Network Security

- **Firewall Rules**: Configure appropriate firewall rules for the server port
- **Access Control**: HTTP mode fails fast on a keyless start by default (`require_auth: true`). Note that per-request API-key enforcement on the served endpoint lands in Phase 3 (REF-07) — see the *Known limitation* note under [Authentication](#-authentication-breaking-change)
- **Network Isolation**: Run in isolated network environments when possible

### Tool Security

- **Privileged Operations**: Some tools require elevated privileges
- **Network Scanning**: Be aware of legal implications of network scanning
- **Rate Limiting**: Implement rate limiting for resource-intensive operations

### Best Practices

- **Input Validation**: All inputs are validated before processing
- **Error Handling**: Comprehensive error handling and logging
- **Timeout Management**: Configurable timeouts for all operations
- **Resource Limits**: Built-in resource usage limits

## 🚀 Production Deployment

### Quick Production Setup

1. **Generate API Keys** (writes `sha256:<hex>` digests into the config and
   enables `require_auth`; the plain keys are printed once — save them):
   ```bash
   python scripts/generate_api_key.py -n 2 --config config/config.json
   ```

2. **Verify Security Settings** (`config/config.json` — only hashed keys are
   accepted; see [Authentication](#-authentication-breaking-change)):
   ```json
   {
     "security": {
       "require_auth": true,
       "api_keys": [
         "sha256:0f70dbbe4175927d0c7ff3bdc45622f13e6a5d306248731395a8995974effe25"
       ],
       "rate_limit_requests": 100,
       "rate_limit_window": 60
     }
   }
   ```

3. **Deploy with Docker Compose**:
   ```bash
   docker compose up -d
   ```

4. **Verify Deployment**:
   ```bash
   curl http://localhost:8815/health
   ```

### Authentication

HTTP mode **refuses to start without a key by default** (`require_auth: true`),
and the server stores and compares only `sha256:` digests — clients send the
plain key. Note that **per-request enforcement on the served endpoint is not yet
active** (lands in Phase 3 / REF-07); see the *Known limitation* note. Full
details (key generation, hashing, opt-out) are in
[Authentication](#-authentication-breaking-change):

```bash
# Make authenticated request (plain key, not the sha256: digest)
curl -X POST http://localhost:8815/netops-mcp \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"method": "ping_host", "params": {"host": "google.com"}}'
```

### HTTPS Setup (Recommended)

Use a reverse proxy (nginx or Caddy) for HTTPS:

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8815;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Production Features

- ✅ **Input Validation**: Comprehensive input sanitization
- ✅ **Structured Logging**: JSON logging for production environments
- ✅ **Docker Support**: Production-ready Docker image with multi-stage build
- ✅ **Non-Root User**: Runs as unprivileged user in container
- ✅ **Resource Limits**: Configurable CPU and memory limits
- ✅ **Auth Startup Gate**: HTTP mode fails fast on a keyless start (`require_auth: true`)

The following are implemented and configurable but are **not yet wired to the
served HTTP app** — enforcement lands in **Phase 3 (REF-07)** (see the *Known
limitation* note under [Authentication](#-authentication-breaking-change)):

- 🔜 **Per-request API Key Authentication**: Bearer / X-API-Key / API-Key headers
- 🔜 **Rate Limiting**: Built-in rate limiting (100 req/min default)
- 🔜 **Health Checks**: `/health` and `/metrics` endpoints
- 🔜 **CORS Support**: Configurable CORS for web applications
- 🔜 **Security Headers**: Automatic security headers

### CI/CD Pipeline

GitHub Actions workflows included:
- **Tests**: Automated testing on Python 3.10, 3.11, 3.12
- **Linting**: Code quality checks (Black, Ruff, mypy)
- **Security**: Security scanning (Bandit, Safety, Trivy)
- **Release**: Automated Docker image publishing to GitHub Container Registry

### Documentation

- 📖 [Production Deployment Guide](docs/PRODUCTION_DEPLOYMENT.md)
- 🔐 [API Authentication Guide](docs/API_AUTHENTICATION.md)
- 🛡️ [Security Policy](SECURITY.md)

## 🤝 Contributing

### Development Setup

```bash
# Clone repository
git clone https://github.com/alpadalar/NetOpsMCP.git
cd NetOpsMCP

# Install development dependencies
uv pip install -e .

# Run tests
pytest tests/ -v
```

### Code Style

- **Black**: Code formatting
- **Ruff**: Linting and import sorting
- **mypy**: Type checking

### Testing Guidelines

- Write tests for all new functionality
- Maintain test coverage above 90%
- Use meaningful test names and descriptions
- Mock external dependencies

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Update documentation
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Documentation

- API Reference: See the API Reference section above
- Configuration Guide: See the Configuration section above  
- Troubleshooting: See the Support section above

### Issues

- **Bug Reports**: Use GitHub Issues
- **Feature Requests**: Submit via GitHub Issues
- **Security Issues**: Contact maintainers directly

### Community

- **Issues**: GitHub Issues for discussions and questions
- **Documentation**: See the sections above for comprehensive guides

## 🙏 Acknowledgments

- **MCP Protocol**: Model Context Protocol specification
- **Network Tools**: Open source networking utilities
- **Testing Framework**: pytest and related tools
- **Community**: Contributors and users

---

**NetOps MCP** - Empowering network operations through standardized tool access.
