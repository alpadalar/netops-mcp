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
git clone <repository-url>
cd NetOpsMCP

# Install dependencies using uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### Using pip

```bash
# Clone the repository
git clone <repository-url>
cd NetOpsMCP

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
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

```bash
# Using Python directly
python -m src.devops_mcp.server_http --host 0.0.0.0 --port 8815

# Using Docker
docker compose up -d

# Using the provided script
./start_http_server.sh
```

### 2. Test the Server

```bash
# Health check
curl http://localhost:8815/devops-mcp/health

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
pytest tests/ --cov=src --cov-report=html
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

## 🔧 Configuration

### Environment Variables

```bash
# Server configuration
DEVOPSCP_HOST=0.0.0.0
DEVOPSCP_PORT=8815
DEVOPSCP_LOG_LEVEL=INFO

# Tool timeouts
PING_TIMEOUT=10
TRACEROUTE_TIMEOUT=30
MTR_TIMEOUT=30
CURL_TIMEOUT=30
NMAP_TIMEOUT=300
```

### Configuration File

Create `config/config.json`:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8815,
    "log_level": "INFO"
  },
  "tools": {
    "timeouts": {
      "ping": 10,
      "traceroute": 30,
      "mtr": 30,
      "curl": 30,
      "nmap": 300
    },
    "defaults": {
      "ping_count": 4,
      "traceroute_max_hops": 30,
      "mtr_count": 10
    }
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
      - NETOPSCP_HOST=0.0.0.0
      - NETOPSCP_PORT=8815
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8815/netops-mcp/health"]
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

- `logs/netopsmcp.log`: Main application log
- `logs/access.log`: HTTP access log
- `logs/error.log`: Error log

### Health Checks

```bash
# Check server health
curl http://localhost:8815/netops-mcp/health

# Check system requirements
curl -X POST http://localhost:8815/netops-mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "check_required_tools", "params": {}}'
```

## 🔒 Security Considerations

### Network Security

- **Firewall Rules**: Configure appropriate firewall rules for the server port
- **Access Control**: Implement authentication if needed
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

## 🤝 Contributing

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd NetOpsMCP

# Install development dependencies
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/ -v
```

### Code Style

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
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

- [API Reference](docs/api.md)
- [Configuration Guide](docs/configuration.md)
- [Troubleshooting](docs/troubleshooting.md)

### Issues

- **Bug Reports**: Use GitHub Issues
- **Feature Requests**: Submit via GitHub Issues
- **Security Issues**: Contact maintainers directly

### Community

- **Discussions**: GitHub Discussions
- **Wiki**: Project Wiki for additional documentation

## 🙏 Acknowledgments

- **MCP Protocol**: Model Context Protocol specification
- **Network Tools**: Open source networking utilities
- **Testing Framework**: pytest and related tools
- **Community**: Contributors and users

---

**NetOps MCP** - Empowering network operations through standardized tool access.
