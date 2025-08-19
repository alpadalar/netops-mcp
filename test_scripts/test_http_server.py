#!/usr/bin/env python3
"""
Test script for DevOpsMCP HTTP server.
"""

import requests
import json
import time
import sys


def test_health_endpoint(base_url):
    """Test health endpoint."""
    print("🔍 Testing health endpoint...")
    
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


def test_tools_endpoint(base_url):
    """Test tools endpoint."""
    print("🔍 Testing tools endpoint...")
    
    try:
        response = requests.get(f"{base_url}/tools", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Tools endpoint: {len(data.get('tools', []))} tools available")
            return True
        else:
            print(f"❌ Tools endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Tools endpoint error: {e}")
        return False


def test_ping_tool(base_url):
    """Test ping tool."""
    print("🔍 Testing ping tool...")
    
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "ping_host",
                "arguments": {
                    "host": "8.8.8.8",
                    "count": 2
                }
            }
        }
        
        response = requests.post(base_url, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if "result" in data:
                print("✅ Ping tool test passed")
                return True
            else:
                print(f"❌ Ping tool failed: {data}")
                return False
        else:
            print(f"❌ Ping tool request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ping tool error: {e}")
        return False


def test_curl_tool(base_url):
    """Test curl tool."""
    print("🔍 Testing curl tool...")
    
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "curl_request",
                "arguments": {
                    "url": "https://httpbin.org/get",
                    "method": "GET",
                    "timeout": 10
                }
            }
        }
        
        response = requests.post(base_url, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if "result" in data:
                print("✅ Curl tool test passed")
                return True
            else:
                print(f"❌ Curl tool failed: {data}")
                return False
        else:
            print(f"❌ Curl tool request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Curl tool error: {e}")
        return False


def test_system_status_tool(base_url):
    """Test system status tool."""
    print("🔍 Testing system status tool...")
    
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "system_status",
                "arguments": {}
            }
        }
        
        response = requests.post(base_url, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if "result" in data:
                print("✅ System status tool test passed")
                return True
            else:
                print(f"❌ System status tool failed: {data}")
                return False
        else:
            print(f"❌ System status tool request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ System status tool error: {e}")
        return False


def main():
    """Main test function."""
    base_url = "http://localhost:8815/devops-mcp"
    
    print("🚀 Starting DevOpsMCP HTTP Server Tests")
    print(f"📍 Server URL: {base_url}")
    print("-" * 50)
    
    tests = [
        test_health_endpoint,
        test_tools_endpoint,
        test_ping_tool,
        test_curl_tool,
        test_system_status_tool
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test(base_url):
            passed += 1
        print()
        time.sleep(1)
    
    print("-" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
