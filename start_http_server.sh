#!/bin/bash

# NetOps MCP HTTP Server Startup Script
# This script starts the NetOps MCP HTTP server with proper configuration

set -e

# Default values
HOST=${HTTP_HOST:-"0.0.0.0"}
PORT=${HTTP_PORT:-"8815"}
PATH=${HTTP_PATH:-"/netops-mcp"}
CONFIG=${NETOPS_MCP_CONFIG:-"config/config.json"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting NetOps MCP HTTP Server${NC}"
echo -e "${YELLOW}Host: ${HOST}${NC}"
echo -e "${YELLOW}Port: ${PORT}${NC}"
echo -e "${YELLOW}Path: ${PATH}${NC}"
echo -e "${YELLOW}Config: ${CONFIG}${NC}"

# Check if config file exists
if [ ! -f "$CONFIG" ]; then
    echo -e "${RED}❌ Config file not found: $CONFIG${NC}"
    echo -e "${YELLOW}Creating default config...${NC}"
    mkdir -p config
    cp config/config.example.json "$CONFIG"
fi

# Check if logs directory exists
if [ ! -d "logs" ]; then
    echo -e "${YELLOW}Creating logs directory...${NC}"
    mkdir -p logs
fi

# Set environment variables
export NETOPS_MCP_CONFIG="$CONFIG"
export HTTP_HOST="$HOST"
export HTTP_PORT="$PORT"
export HTTP_PATH="$PATH"

# Start the server
echo -e "${GREEN}✅ Starting server...${NC}"
python -m netops_mcp.server_http \
    --host "$HOST" \
    --port "$PORT" \
    --path "$PATH" \
    --config "$CONFIG"
