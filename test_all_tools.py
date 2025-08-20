#!/usr/bin/env python3
"""
Test all 26 NetOps MCP tools.
"""

import sys
import os
sys.path.insert(0, '/app/src')

from netops_mcp.tools.network.http_tools import HTTPTools
from netops_mcp.tools.network.connectivity_tools import ConnectivityTools
from netops_mcp.tools.network.dns_tools import DNSTools
from netops_mcp.tools.network.discovery_tools import DiscoveryTools
from netops_mcp.tools.system.network_tools import NetworkTools
from netops_mcp.tools.system.monitoring_tools import MonitoringTools
from netops_mcp.tools.security.scanning_tools import ScanningTools
from netops_mcp.utils.system_check import check_required_tools, get_system_info

def test_http_tools():
    """Test HTTP/API Testing Tools (3 tools)."""
    print("🔧 Testing HTTP/API Testing Tools...")
    tools = HTTPTools()
    
    # Test curl_request
    print("  📡 Testing curl_request...")
    try:
        result = tools.curl_request("https://httpbin.org/get", method="GET", timeout=10)
        print(f"    ✅ curl_request: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ curl_request failed: {e}")
    
    # Test httpie_request
    print("  📡 Testing httpie_request...")
    try:
        result = tools.httpie_request("https://httpbin.org/get", method="GET", timeout=10)
        print(f"    ✅ httpie_request: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ httpie_request failed: {e}")
    
    # Test api_test
    print("  📡 Testing api_test...")
    try:
        result = tools.api_test("https://httpbin.org/get", method="GET", expected_status=200, timeout=10)
        print(f"    ✅ api_test: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ api_test failed: {e}")

def test_connectivity_tools():
    """Test Network Connectivity Tools (5 tools)."""
    print("🔧 Testing Network Connectivity Tools...")
    tools = ConnectivityTools()
    
    # Test ping_host
    print("  📡 Testing ping_host...")
    try:
        result = tools.ping_host("8.8.8.8", count=2, timeout=10)
        print(f"    ✅ ping_host: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ ping_host failed: {e}")
    
    # Test traceroute_path
    print("  📡 Testing traceroute_path...")
    try:
        result = tools.traceroute_path("8.8.8.8", max_hops=5, timeout=10)
        print(f"    ✅ traceroute_path: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ traceroute_path failed: {e}")
    
    # Test mtr_monitor
    print("  📡 Testing mtr_monitor...")
    try:
        result = tools.mtr_monitor("8.8.8.8", count=3, timeout=10)
        print(f"    ✅ mtr_monitor: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ mtr_monitor failed: {e}")
    
    # Test telnet_connect
    print("  📡 Testing telnet_connect...")
    try:
        result = tools.telnet_connect("8.8.8.8", port=53, timeout=5)
        print(f"    ✅ telnet_connect: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ telnet_connect failed: {e}")
    
    # Test netcat_test
    print("  📡 Testing netcat_test...")
    try:
        result = tools.netcat_test("8.8.8.8", port=53, timeout=5)
        print(f"    ✅ netcat_test: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ netcat_test failed: {e}")

def test_dns_tools():
    """Test DNS Tools (3 tools)."""
    print("🔧 Testing DNS Tools...")
    tools = DNSTools()
    
    # Test nslookup_query
    print("  📡 Testing nslookup_query...")
    try:
        result = tools.nslookup_query("google.com", record_type="A")
        print(f"    ✅ nslookup_query: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ nslookup_query failed: {e}")
    
    # Test dig_query
    print("  📡 Testing dig_query...")
    try:
        result = tools.dig_query("google.com", record_type="A")
        print(f"    ✅ dig_query: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ dig_query failed: {e}")
    
    # Test host_lookup
    print("  📡 Testing host_lookup...")
    try:
        result = tools.host_lookup("google.com", record_type="A")
        print(f"    ✅ host_lookup: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ host_lookup failed: {e}")

def test_discovery_tools():
    """Test Network Discovery Tools (2 tools)."""
    print("🔧 Testing Network Discovery Tools...")
    tools = DiscoveryTools()
    
    # Test nmap_scan
    print("  📡 Testing nmap_scan...")
    try:
        result = tools.nmap_scan("127.0.0.1", ports="22,80,443", scan_type="basic", timeout=30)
        print(f"    ✅ nmap_scan: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ nmap_scan failed: {e}")
    
    # Test service_discovery
    print("  📡 Testing service_discovery...")
    try:
        result = tools.service_discovery("127.0.0.1", ports="22,80,443")
        print(f"    ✅ service_discovery: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ service_discovery failed: {e}")

def test_network_tools():
    """Test System Network Tools (4 tools)."""
    print("🔧 Testing System Network Tools...")
    tools = NetworkTools()
    
    # Test ss_connections
    print("  📡 Testing ss_connections...")
    try:
        result = tools.ss_connections()
        print(f"    ✅ ss_connections: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ ss_connections failed: {e}")
    
    # Test netstat_connections
    print("  📡 Testing netstat_connections...")
    try:
        result = tools.netstat_connections()
        print(f"    ✅ netstat_connections: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ netstat_connections failed: {e}")
    
    # Test arp_table
    print("  📡 Testing arp_table...")
    try:
        result = tools.arp_table()
        print(f"    ✅ arp_table: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ arp_table failed: {e}")
    
    # Test arping_host
    print("  📡 Testing arping_host...")
    try:
        result = tools.arping_host("127.0.0.1", count=2)
        print(f"    ✅ arping_host: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ arping_host failed: {e}")

def test_monitoring_tools():
    """Test System Monitoring Tools (5 tools)."""
    print("🔧 Testing System Monitoring Tools...")
    tools = MonitoringTools()
    
    # Test system_status
    print("  📡 Testing system_status...")
    try:
        result = tools.system_status()
        print(f"    ✅ system_status: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ system_status failed: {e}")
    
    # Test cpu_usage
    print("  📡 Testing cpu_usage...")
    try:
        result = tools.cpu_usage()
        print(f"    ✅ cpu_usage: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ cpu_usage failed: {e}")
    
    # Test memory_usage
    print("  📡 Testing memory_usage...")
    try:
        result = tools.memory_usage()
        print(f"    ✅ memory_usage: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ memory_usage failed: {e}")
    
    # Test disk_usage
    print("  📡 Testing disk_usage...")
    try:
        result = tools.disk_usage()
        print(f"    ✅ disk_usage: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ disk_usage failed: {e}")
    
    # Test process_list
    print("  📡 Testing process_list...")
    try:
        result = tools.process_list(limit=5)
        print(f"    ✅ process_list: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ process_list failed: {e}")

def test_scanning_tools():
    """Test Security Tools (2 tools)."""
    print("🔧 Testing Security Tools...")
    tools = ScanningTools()
    
    # Test port_scan
    print("  📡 Testing port_scan...")
    try:
        result = tools.port_scan("127.0.0.1", ports="22,80,443", timeout=30)
        print(f"    ✅ port_scan: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ port_scan failed: {e}")
    
    # Test service_enumeration
    print("  📡 Testing service_enumeration...")
    try:
        result = tools.service_enumeration("127.0.0.1", ports="22,80,443")
        print(f"    ✅ service_enumeration: {len(result)} content items")
    except Exception as e:
        print(f"    ❌ service_enumeration failed: {e}")

def test_system_tools():
    """Test System Tools (2 tools)."""
    print("🔧 Testing System Tools...")
    
    # Test check_required_tools
    print("  📡 Testing check_required_tools...")
    try:
        result = check_required_tools()
        print(f"    ✅ check_required_tools: {result}")
    except Exception as e:
        print(f"    ❌ check_required_tools failed: {e}")
    
    # Test get_system_info
    print("  📡 Testing get_system_info...")
    try:
        result = get_system_info()
        print(f"    ✅ get_system_info: {result}")
    except Exception as e:
        print(f"    ❌ get_system_info failed: {e}")

def main():
    """Main function to test all tools."""
    print("🚀 Testing All 26 NetOps MCP Tools")
    print("=" * 60)
    
    # Test all tool categories
    test_http_tools()
    print()
    
    test_connectivity_tools()
    print()
    
    test_dns_tools()
    print()
    
    test_discovery_tools()
    print()
    
    test_network_tools()
    print()
    
    test_monitoring_tools()
    print()
    
    test_scanning_tools()
    print()
    
    test_system_tools()
    print()
    
    print("🎯 All 26 tools tested!")
    print("=" * 60)

if __name__ == "__main__":
    main()
