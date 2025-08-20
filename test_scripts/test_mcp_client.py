#!/usr/bin/env python3
"""
MCP Client test script for NetOpsMCP.
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_netops_tools():
    """Test NetOps tools via MCP."""
    print("🚀 Testing NetOpsMCP Tools via MCP Client")
    print("-" * 50)
    
    # Connect to the server
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "netops_mcp.server"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()
            
            # List available tools
            print("📋 Available tools:")
            tools = await session.list_tools()
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
            
            print("\n" + "-" * 50)
            
            # Test ping tool
            print("🔍 Testing ping tool...")
            try:
                result = await session.call_tool("ping_host", {
                    "host": "8.8.8.8",
                    "count": 3
                })
                print("✅ Ping tool result:")
                print(json.dumps(result.content, indent=2))
            except Exception as e:
                print(f"❌ Ping tool failed: {e}")
            
            print("\n" + "-" * 50)
            
            # Test curl tool
            print("🔍 Testing curl tool...")
            try:
                result = await session.call_tool("curl_request", {
                    "url": "https://httpbin.org/get",
                    "method": "GET",
                    "timeout": 10
                })
                print("✅ Curl tool result:")
                print(json.dumps(result.content, indent=2))
            except Exception as e:
                print(f"❌ Curl tool failed: {e}")
            
            print("\n" + "-" * 50)
            
            # Test system status
            print("🔍 Testing system status...")
            try:
                result = await session.call_tool("system_status", {})
                print("✅ System status result:")
                print(json.dumps(result.content, indent=2))
            except Exception as e:
                print(f"❌ System status failed: {e}")


async def test_http_server():
    """Test HTTP server via MCP."""
    print("🚀 Testing NetOpsMCP HTTP Server")
    print("-" * 50)
    
    # This would require a different approach for HTTP transport
    print("⚠️  HTTP transport testing requires different client implementation")
    print("   The server is running on http://localhost:8815/netops-mcp")


def main():
    """Main function."""
    print("🎯 NetOpsMCP Tool Testing")
    print("=" * 50)
    
    # Test stdio transport
    try:
        asyncio.run(test_netops_tools())
    except Exception as e:
        print(f"❌ Stdio transport test failed: {e}")
    
    print("\n" + "=" * 50)
    
    # Test HTTP transport
    test_http_server()


if __name__ == "__main__":
    main()
