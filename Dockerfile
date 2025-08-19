# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies and network diagnostic tools
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
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
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install uv

# Copy project files
COPY . .

# Create virtual environment and install dependencies
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install -e ".[dev]" && \
    uv pip install fastmcp asgiref fastapi

# Create necessary directories
RUN mkdir -p /app/logs /app/config

# Expose port
EXPOSE 8815

# Set environment variables
ENV NETOPS_MCP_CONFIG="/app/config/config.json"
ENV HTTP_HOST="0.0.0.0"
ENV HTTP_PORT="8815"
ENV HTTP_PATH="/netops-mcp"

# Startup command - HTTP MCP Server
CMD ["/bin/bash", "-c", "cd /app && source .venv/bin/activate && python -m netops_mcp.server_http --host ${HTTP_HOST} --port ${HTTP_PORT} --path ${HTTP_PATH}"]
