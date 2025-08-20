#!/usr/bin/env python3
"""
Simple test script for NetOpsMCP HTTP server.
"""

import requests
import json
import time


def test_server_connection():
    """Test basic server connection."""
    print("🔍 Testing server connection...")
    
    try:
        response = requests.get("http://localhost:8815/netops-mcp", timeout=10)
        print(f"✅ Server is running: {response.status_code}")
        print(f"📄 Response: {response.text[:200]}...")
        return True
    except Exception as e:
        print(f"❌ Server connection failed: {e}")
        return False


def test_curl_command():
    """Test curl command directly."""
    print("🔍 Testing curl command...")
    
    try:
        import subprocess
        result = subprocess.run(['curl', '-s', 'http://localhost:8815/netops-mcp'], 
                              capture_output=True, text=True, timeout=10)
        print(f"✅ Curl command successful: {result.returncode}")
        print(f"📄 Response: {result.stdout[:200]}...")
        return True
    except Exception as e:
        print(f"❌ Curl command failed: {e}")
        return False


def main():
    """Main test function."""
    print("🚀 Starting Simple NetOpsMCP Tests")
    print("📍 Server URL: http://localhost:8815/netops-mcp")
    print("-" * 50)
    
    tests = [
        test_server_connection,
        test_curl_command
    ]
    
    for test in tests:
        test()
        print()
        time.sleep(1)
    
    print("-" * 50)
    print("✅ Basic tests completed!")


if __name__ == "__main__":
    main()
