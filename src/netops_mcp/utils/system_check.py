"""
System check utilities for DevOps MCP server.

This module provides utilities for checking system requirements and
required tools availability.
"""

import subprocess
import shutil
from typing import Dict, List, Tuple


def check_required_tools() -> Dict[str, bool]:
    """Check if required system tools are available.

    Returns:
        Dictionary mapping tool names to availability status
    """
    required_tools = [
        'curl', 'ping', 'traceroute', 'mtr', 'telnet', 'nc',
        'nmap', 'netstat', 'ss', 'nslookup', 'dig', 'host',
        'arp', 'arping', 'httpie'
    ]
    
    results = {}
    for tool in required_tools:
        results[tool] = shutil.which(tool) is not None
    
    return results


def check_tool_version(tool_name: str) -> Tuple[bool, str]:
    """Check if a specific tool is available and get its version.

    Args:
        tool_name: Name of the tool to check

    Returns:
        Tuple of (available, version_info)
    """
    if not shutil.which(tool_name):
        return False, "Tool not found"
    
    try:
        # Try to get version information
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
            return True, version_line
        else:
            return True, "Version unknown"
            
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return True, "Version check failed"


def get_system_info() -> Dict[str, str]:
    """Get basic system information.

    Returns:
        Dictionary containing system information
    """
    import platform
    import psutil
    
    info = {
        'platform': platform.system(),
        'platform_version': platform.version(),
        'architecture': platform.machine(),
        'python_version': platform.python_version(),
        'cpu_count': str(psutil.cpu_count()),
        'memory_total': f"{psutil.virtual_memory().total // (1024**3)} GB"
    }
    
    return info


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
