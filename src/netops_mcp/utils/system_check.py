"""
System check utilities for NetOps MCP server.

This module provides utilities for checking system requirements and
required tools availability.
"""

import subprocess
import shutil
import platform
import psutil
from typing import Dict, List, Tuple, Any

# Required tools for the MCP server
REQUIRED_TOOLS = [
    'curl', 'ping', 'traceroute', 'mtr', 'telnet', 'nc',
    'nmap', 'netstat', 'ss', 'nslookup', 'dig', 'host',
    'arp', 'arping', 'httpie'
]


def check_required_tools(tools: List[str] = None) -> Dict[str, Any]:
    """Check if required system tools are available.

    Args:
        tools: List of tools to check. If None, uses REQUIRED_TOOLS.

    Returns:
        Dictionary with availability status and lists of available/missing tools
    """
    if tools is None:
        tools = REQUIRED_TOOLS
    
    available_tools = []
    missing_tools = []
    
    for tool in tools:
        if is_tool_available(tool):
            available_tools.append(tool)
        else:
            missing_tools.append(tool)
    
    return {
        'all_available': len(missing_tools) == 0,
        'available_tools': available_tools,
        'missing_tools': missing_tools
    }


def is_tool_available(tool_name: str) -> bool:
    """Check if a specific tool is available.

    Args:
        tool_name: Name of the tool to check

    Returns:
        True if tool is available, False otherwise
    """
    try:
        # Try to get version information to check availability
        if tool_name == 'curl':
            result = subprocess.run(['curl', '--version'], 
                                  capture_output=True, text=True, timeout=5)
        elif tool_name == 'nmap':
            result = subprocess.run(['nmap', '--version'], 
                                  capture_output=True, text=True, timeout=5)
        elif tool_name == 'ping':
            result = subprocess.run(['ping', '-V'], 
                                  capture_output=True, text=True, timeout=5)
        else:
            result = subprocess.run([tool_name, '--version'], 
                                  capture_output=True, text=True, timeout=5)
        
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, subprocess.SubprocessError):
        return False


def get_tool_version(tool_name: str) -> str:
    """Get version information for a specific tool.

    Args:
        tool_name: Name of the tool to get version for

    Returns:
        Version string or "Unknown" if not available
    """
    try:
        if tool_name == 'curl':
            result = subprocess.run(['curl', '--version'], 
                                  capture_output=True, text=True, timeout=5)
        elif tool_name == 'nmap':
            result = subprocess.run(['nmap', '--version'], 
                                  capture_output=True, text=True, timeout=5)
        elif tool_name == 'ping':
            result = subprocess.run(['ping', '-V'], 
                                  capture_output=True, text=True, timeout=5)
        else:
            result = subprocess.run([tool_name, '--version'], 
                                  capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            return version_line
        else:
            return "Unknown"
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, subprocess.SubprocessError):
        return "Unknown"


def check_tool_version(tool_name: str) -> Tuple[bool, str]:
    """Check if a specific tool is available and get its version.

    Args:
        tool_name: Name of the tool to check

    Returns:
        Tuple of (available, version_info)
    """
    available = is_tool_available(tool_name)
    version = get_tool_version(tool_name) if available else "Tool not found"
    return available, version


def get_system_info() -> Dict[str, Any]:
    """Get basic system information.

    Returns:
        Dictionary containing system information
    """
    try:
        cpu_count = psutil.cpu_count()
    except Exception:
        cpu_count = "Unknown"
    
    try:
        memory_total = psutil.virtual_memory().total
    except Exception:
        memory_total = "Unknown"
    
    info = {
        'platform': platform.system(),
        'python_version': platform.python_version(),
        'architecture': platform.machine(),
        'hostname': platform.node(),
        'cpu_count': cpu_count,
        'memory_total': memory_total
    }
    
    return info


def validate_system_requirements() -> Dict[str, Any]:
    """Validate system requirements for the MCP server.

    Returns:
        Dictionary with validation results
    """
    tools_check = check_required_tools()
    system_info = get_system_info()
    
    return {
        'valid': tools_check['all_available'],
        'missing_tools': tools_check['missing_tools'],
        'system_info': system_info
    }


def get_network_interfaces() -> Dict[str, List[Dict[str, str]]]:
    """Get network interfaces information.

    Returns:
        Dictionary mapping interface names to their addresses
    """
    try:
        interfaces = {}
        for interface, addrs in psutil.net_if_addrs().items():
            interfaces[interface] = []
            for addr in addrs:
                interfaces[interface].append({
                    'family': str(addr.family),
                    'address': addr.address,
                    'netmask': addr.netmask
                })
        return interfaces
    except Exception:
        return {}


def get_disk_usage(path: str = '/') -> Dict[str, int]:
    """Get disk usage information for a path.

    Args:
        path: Path to check disk usage for

    Returns:
        Dictionary with disk usage information
    """
    try:
        usage = psutil.disk_usage(path)
        return {
            'total': usage.total,
            'used': usage.used,
            'free': usage.free,
            'percent': usage.percent
        }
    except Exception:
        return {
            'total': 0,
            'used': 0,
            'free': 0,
            'percent': 0.0
        }


def get_memory_info() -> Dict[str, int]:
    """Get memory information.

    Returns:
        Dictionary with memory information
    """
    try:
        memory = psutil.virtual_memory()
        return {
            'total': memory.total,
            'available': memory.available,
            'used': memory.used,
            'percent': memory.percent
        }
    except Exception:
        return {
            'total': 0,
            'available': 0,
            'used': 0,
            'percent': 0.0
        }


def get_cpu_info() -> Dict[str, Any]:
    """Get CPU information.

    Returns:
        Dictionary with CPU information
    """
    try:
        return {
            'count': psutil.cpu_count(),
            'usage_percent': psutil.cpu_percent(interval=1)
        }
    except Exception:
        return {
            'count': 0,
            'usage_percent': 0.0
        }


def validate_network_access(host: str = "8.8.8.8") -> bool:
    """Validate basic network access.

    Args:
        host: Host to test connectivity with

    Returns:
        True if network access is available
    """
    try:
        result = subprocess.run(['ping', '-c', '1', '-W', '5', host], 
                              capture_output=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_privileged_access() -> Dict[str, bool]:
    """Check if privileged access is available for certain tools.

    Returns:
        Dictionary of privilege checks
    """
    checks = {
        'can_ping': False,
        'can_traceroute': False,
        'can_nmap': False,
        'can_arp': False
    }
    
    try:
        # Test ping
        result = subprocess.run(['ping', '-c', '1', '127.0.0.1'], 
                              capture_output=True, timeout=5)
        checks['can_ping'] = result.returncode == 0
    except:
        pass
    
    try:
        # Test traceroute
        result = subprocess.run(['traceroute', '-m', '1', '127.0.0.1'], 
                              capture_output=True, timeout=5)
        checks['can_traceroute'] = result.returncode == 0
    except:
        pass
    
    try:
        # Test nmap
        result = subprocess.run(['nmap', '-sn', '127.0.0.1'], 
                              capture_output=True, timeout=5)
        checks['can_nmap'] = result.returncode == 0
    except:
        pass
    
    try:
        # Test arp
        result = subprocess.run(['arp', '-a'], 
                              capture_output=True, timeout=5)
        checks['can_arp'] = result.returncode == 0
    except:
        pass
    
    return checks
