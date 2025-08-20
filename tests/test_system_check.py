"""
Tests for the system check module.
"""
import pytest
import subprocess
import platform
import psutil
from unittest.mock import Mock, patch, MagicMock
from netops_mcp.utils.system_check import (
    check_required_tools,
    get_system_info,
    is_tool_available,
    get_tool_version,
    validate_system_requirements,
    get_network_interfaces,
    get_disk_usage,
    get_memory_info,
    get_cpu_info
)


class TestSystemCheck:
    """Test cases for system check utilities."""

    @patch('netops_mcp.utils.system_check.subprocess.run')
    def test_check_required_tools_all_available(self, mock_run):
        """Test checking required tools when all are available."""
        mock_run.return_value = Mock(returncode=0)
        
        tools = ['ping', 'curl', 'nslookup']
        result = check_required_tools(tools)
        
        assert result['all_available'] is True
        assert len(result['available_tools']) == 3
        assert len(result['missing_tools']) == 0
        assert 'ping' in result['available_tools']
        assert 'curl' in result['available_tools']
        assert 'nslookup' in result['available_tools']

    @patch('netops_mcp.utils.system_check.subprocess.run')
    def test_check_required_tools_some_missing(self, mock_run):
        """Test checking required tools when some are missing."""
        def mock_run_side_effect(cmd, **kwargs):
            if 'ping' in cmd:
                return Mock(returncode=0)
            else:
                return Mock(returncode=1)
        
        mock_run.side_effect = mock_run_side_effect
        
        tools = ['ping', 'nonexistent_tool', 'another_missing']
        result = check_required_tools(tools)
        
        assert result['all_available'] is False
        assert len(result['available_tools']) == 1
        assert len(result['missing_tools']) == 2
        assert 'ping' in result['available_tools']
        assert 'nonexistent_tool' in result['missing_tools']
        assert 'another_missing' in result['missing_tools']

    @patch('netops_mcp.utils.system_check.subprocess.run')
    def test_check_required_tools_all_missing(self, mock_run):
        """Test checking required tools when all are missing."""
        mock_run.return_value = Mock(returncode=1)
        
        tools = ['missing1', 'missing2', 'missing3']
        result = check_required_tools(tools)
        
        assert result['all_available'] is False
        assert len(result['available_tools']) == 0
        assert len(result['missing_tools']) == 3

    @patch('netops_mcp.utils.system_check.subprocess.run')
    def test_check_required_tools_empty_list(self, mock_run):
        """Test checking required tools with empty list."""
        result = check_required_tools([])
        
        assert result['all_available'] is True
        assert len(result['available_tools']) == 0
        assert len(result['missing_tools']) == 0
        mock_run.assert_not_called()

    @patch('netops_mcp.utils.system_check.subprocess.run')
    def test_check_required_tools_subprocess_error(self, mock_run):
        """Test checking required tools when subprocess fails."""
        mock_run.side_effect = subprocess.SubprocessError("Command not found")
        
        tools = ['ping']
        result = check_required_tools(tools)
        
        assert result['all_available'] is False
        assert len(result['available_tools']) == 0
        assert len(result['missing_tools']) == 1
        assert 'ping' in result['missing_tools']

    def test_get_system_info(self):
        """Test getting system information."""
        info = get_system_info()
        
        assert isinstance(info, dict)
        assert 'platform' in info
        assert 'python_version' in info
        assert 'architecture' in info
        assert 'hostname' in info
        assert 'cpu_count' in info
        assert 'memory_total' in info
        
        assert info['platform'] == platform.system()
        assert info['python_version'] == platform.python_version()
        assert info['architecture'] == platform.machine()
        assert info['hostname'] == platform.node()
        assert info['cpu_count'] == psutil.cpu_count()

    @patch('netops_mcp.utils.system_check.subprocess.run')
    def test_is_tool_available_true(self, mock_run):
        """Test checking if a tool is available (returns True)."""
        mock_run.return_value = Mock(returncode=0)
        
        result = is_tool_available('ping')
        
        assert result is True
        mock_run.assert_called_once()

    @patch('netops_mcp.utils.system_check.subprocess.run')
    def test_is_tool_available_false(self, mock_run):
        """Test checking if a tool is available (returns False)."""
        mock_run.return_value = Mock(returncode=1)
        
        result = is_tool_available('nonexistent_tool')
        
        assert result is False
        mock_run.assert_called_once()

    @patch('netops_mcp.utils.system_check.subprocess.run')
    def test_is_tool_available_subprocess_error(self, mock_run):
        """Test checking if a tool is available when subprocess fails."""
        mock_run.side_effect = subprocess.SubprocessError("Command not found")
        
        result = is_tool_available('ping')
        
        assert result is False

    @patch('netops_mcp.utils.system_check.subprocess.run')
    def test_get_tool_version_success(self, mock_run):
        """Test getting tool version successfully."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="curl 7.68.0 (x86_64-pc-linux-gnu)\n"
        )
        
        version = get_tool_version('curl')
        
        assert version == "curl 7.68.0 (x86_64-pc-linux-gnu)"
        mock_run.assert_called_once()

    @patch('netops_mcp.utils.system_check.subprocess.run')
    def test_get_tool_version_failure(self, mock_run):
        """Test getting tool version when command fails."""
        mock_run.return_value = Mock(returncode=1, stdout=b"")
        
        version = get_tool_version('nonexistent_tool')
        
        assert version == "Unknown"
        mock_run.assert_called_once()

    @patch('netops_mcp.utils.system_check.subprocess.run')
    def test_get_tool_version_subprocess_error(self, mock_run):
        """Test getting tool version when subprocess fails."""
        mock_run.side_effect = subprocess.SubprocessError("Command not found")
        
        version = get_tool_version('ping')
        
        assert version == "Unknown"

    def test_validate_system_requirements(self):
        """Test system requirements validation."""
        # Mock the required tools check
        with patch('netops_mcp.utils.system_check.check_required_tools') as mock_check:
            mock_check.return_value = {
                'all_available': True,
                'available_tools': ['ping', 'curl', 'nslookup'],
                'missing_tools': []
            }
            
            result = validate_system_requirements()
            
            assert result['valid'] is True
            assert result['missing_tools'] == []
            assert 'system_info' in result

    def test_validate_system_requirements_missing_tools(self):
        """Test system requirements validation with missing tools."""
        with patch('netops_mcp.utils.system_check.check_required_tools') as mock_check:
            mock_check.return_value = {
                'all_available': False,
                'available_tools': ['ping'],
                'missing_tools': ['nmap', 'mtr']
            }
            
            result = validate_system_requirements()
            
            assert result['valid'] is False
            assert 'nmap' in result['missing_tools']
            assert 'mtr' in result['missing_tools']
            assert 'system_info' in result

    @patch('netops_mcp.utils.system_check.psutil.net_if_addrs')
    def test_get_network_interfaces(self, mock_net_if_addrs):
        """Test getting network interfaces information."""
        mock_net_if_addrs.return_value = {
            'lo': [
                Mock(family=2, address='127.0.0.1', netmask='255.0.0.0'),
                Mock(family=10, address='::1', netmask='ffff:ffff:ffff:ffff::')
            ],
            'eth0': [
                Mock(family=2, address='192.168.1.100', netmask='255.255.255.0')
            ]
        }
        
        interfaces = get_network_interfaces()
        
        assert isinstance(interfaces, dict)
        assert 'lo' in interfaces
        assert 'eth0' in interfaces
        assert len(interfaces['lo']) == 2
        assert len(interfaces['eth0']) == 1

    @patch('netops_mcp.utils.system_check.psutil.disk_usage')
    def test_get_disk_usage(self, mock_disk_usage):
        """Test getting disk usage information."""
        mock_disk_usage.return_value = Mock(
            total=1000000000,
            used=500000000,
            free=500000000,
            percent=50.0
        )
        
        usage = get_disk_usage('/')
        
        assert isinstance(usage, dict)
        assert 'total' in usage
        assert 'used' in usage
        assert 'free' in usage
        assert 'percent' in usage
        assert usage['total'] == 1000000000
        assert usage['used'] == 500000000
        assert usage['free'] == 500000000
        assert usage['percent'] == 50.0

    @patch('netops_mcp.utils.system_check.psutil.virtual_memory')
    def test_get_memory_info(self, mock_virtual_memory):
        """Test getting memory information."""
        mock_virtual_memory.return_value = Mock(
            total=8000000000,
            available=4000000000,
            used=4000000000,
            percent=50.0
        )
        
        memory = get_memory_info()
        
        assert isinstance(memory, dict)
        assert 'total' in memory
        assert 'available' in memory
        assert 'used' in memory
        assert 'percent' in memory
        assert memory['total'] == 8000000000
        assert memory['available'] == 4000000000
        assert memory['used'] == 4000000000
        assert memory['percent'] == 50.0

    @patch('netops_mcp.utils.system_check.psutil.cpu_percent')
    @patch('netops_mcp.utils.system_check.psutil.cpu_count')
    def test_get_cpu_info(self, mock_cpu_count, mock_cpu_percent):
        """Test getting CPU information."""
        mock_cpu_count.return_value = 8
        mock_cpu_percent.return_value = 25.5
        
        cpu = get_cpu_info()
        
        assert isinstance(cpu, dict)
        assert 'count' in cpu
        assert 'usage_percent' in cpu
        assert cpu['count'] == 8
        assert cpu['usage_percent'] == 25.5

    def test_required_tools_list(self):
        """Test that the required tools list contains expected tools."""
        from netops_mcp.utils.system_check import REQUIRED_TOOLS
        
        expected_tools = [
            'ping', 'traceroute', 'mtr', 'telnet', 'nc', 'curl',
            'nslookup', 'dig', 'host', 'nmap', 'ss', 'netstat',
            'arp', 'arping', 'httpie'
        ]
        
        for tool in expected_tools:
            assert tool in REQUIRED_TOOLS

    @patch('netops_mcp.utils.system_check.subprocess.run')
    def test_tool_check_with_version_flag(self, mock_run):
        """Test that tool checking uses appropriate version flags."""
        mock_run.return_value = Mock(returncode=0, stdout=b"version info")
        
        is_tool_available('curl')
        
        # Check that the command includes --version or -V
        call_args = mock_run.call_args
        command = ' '.join(call_args[0][0])
        assert '--version' in command or '-V' in command

    def test_system_info_structure(self):
        """Test that system info has the correct structure."""
        info = get_system_info()
        
        required_keys = [
            'platform', 'python_version', 'architecture',
            'hostname', 'cpu_count', 'memory_total'
        ]
        
        for key in required_keys:
            assert key in info
            assert info[key] is not None

    @patch('netops_mcp.utils.system_check.psutil')
    def test_system_info_with_psutil_error(self, mock_psutil):
        """Test system info when psutil operations fail."""
        mock_psutil.cpu_count.side_effect = Exception("CPU count error")
        mock_psutil.virtual_memory.side_effect = Exception("Memory error")
        
        info = get_system_info()
        
        # Should still return basic info even if psutil fails
        assert 'platform' in info
        assert 'python_version' in info
        assert 'architecture' in info
        assert 'hostname' in info
        # CPU and memory might be None or have default values
        assert 'cpu_count' in info
        assert 'memory_total' in info
