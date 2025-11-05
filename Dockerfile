# Multi-stage build for smaller, more secure image
# Stage 1: Builder
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml requirements.in requirements-dev.in ./
COPY src/ ./src/

# Create virtual environment and install dependencies
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache .

# Stage 2: Runtime
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime system dependencies and network diagnostic tools
RUN apt-get update && apt-get install -y \
    curl \
    iputils-ping \
    traceroute \
    mtr \
    telnet \
    netcat-openbsd \
    nmap \
    net-tools \
    iproute2 \
    dnsutils \
    iputils-arping \
    httpie \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r netopsmcp && \
    useradd -r -g netopsmcp -u 1000 -m -s /sbin/nologin netopsmcp

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=netopsmcp:netopsmcp src/ ./src/
COPY --chown=netopsmcp:netopsmcp pyproject.toml ./
COPY --chown=netopsmcp:netopsmcp config/config.example.json ./config/

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/config && \
    chown -R netopsmcp:netopsmcp /app/logs /app/config

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV NETOPS_MCP_CONFIG="/app/config/config.json"
ENV HTTP_HOST="0.0.0.0"
ENV HTTP_PORT="8815"
ENV HTTP_PATH="/netops-mcp"

# Expose port
EXPOSE 8815

# Switch to non-root user
USER netopsmcp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8815/health || exit 1

# Startup command - HTTP MCP Server
CMD ["python", "-m", "netops_mcp.server_http", "--host", "0.0.0.0", "--port", "8815", "--path", "/netops-mcp"]
