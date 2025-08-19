#!/usr/bin/env python3
"""
HTTP Client test script for DevOpsMCP.
"""

import requests
import json
import time


def test_mcp_http_request(method, params=None):
    """Test MCP HTTP request."""
    url = "http://localhost:8815/devops-mcp"
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
    }
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {}
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"📡 Request: {method}")
        print(f"📊 Status: {response.status_code}")
        print(f"📄 Response: {response.text[:500]}...")
        return response
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None


def test_tools_list():
    """Test tools list."""
    print("🔍 Testing tools list...")
    return test_mcp_http_request("tools/list")


def test_ping_tool():
    """Test ping tool."""
    print("🔍 Testing ping tool...")
    return test_mcp_http_request("tools/call", {
        "name": "ping_host",
        "arguments": {
            "host": "8.8.8.8",
            "count": 2
        }
    })


def test_curl_tool():
    """Test curl tool."""
    print("🔍 Testing curl tool...")
    return test_mcp_http_request("tools/call", {
        "name": "curl_request",
        "arguments": {
            "url": "https://httpbin.org/get",
            "method": "GET",
            "timeout": 10
        }
    })


def test_system_status():
    """Test system status."""
    print("🔍 Testing system status...")
    return test_mcp_http_request("tools/call", {
        "name": "system_status",
        "arguments": {}
    })


def test_nslookup():
    """Test nslookup tool."""
    print("🔍 Testing nslookup tool...")
    return test_mcp_http_request("tools/call", {
        "name": "nslookup_query",
        "arguments": {
            "domain": "google.com",
            "record_type": "A"
        }
    })


def test_ss_connections():
    """Test ss connections tool."""
    print("🔍 Testing ss connections tool...")
    return test_mcp_http_request("tools/call", {
        "name": "ss_connections",
        "arguments": {}
    })


def main():
    """Main test function."""
    print("🚀 DevOpsMCP HTTP Client Testing")
    print("📍 Server: http://localhost:8815/devops-mcp")
    print("=" * 60)
    
    tests = [
        ("Tools List", test_tools_list),
        ("Ping Tool", test_ping_tool),
        ("Curl Tool", test_curl_tool),
        ("System Status", test_system_status),
        ("NSLookup", test_nslookup),
        ("SS Connections", test_ss_connections)
    ]
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        print("-" * 40)
        response = test_func()
        
        if response and response.status_code == 200:
            print("✅ Test passed!")
        else:
            print("❌ Test failed!")
        
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print("🎯 Testing completed!")


if __name__ == "__main__":
    main()
