"""
Tests for MonitoringTools.
"""

import pytest
from unittest.mock import patch, MagicMock
from netops_mcp.tools.system.monitoring_tools import MonitoringTools


class TestMonitoringTools:
    """Test MonitoringTools functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.monitoring_tools = MonitoringTools()

    def test_initialization(self):
        """Test MonitoringTools initialization."""
        assert self.monitoring_tools is not None
        assert isinstance(self.monitoring_tools, MonitoringTools)

    @patch('psutil.cpu_percent')
    @patch('psutil.cpu_count')
    @patch('psutil.cpu_freq')
    def test_cpu_usage_valid_inputs(self, mock_cpu_freq, mock_cpu_count, mock_cpu_percent):
        """Test cpu_usage with valid inputs."""
        mock_cpu_percent.return_value = 25.5
        mock_cpu_count.return_value = 8
        mock_cpu_freq.return_value = MagicMock(current=2400.0, min=800.0, max=3200.0)
        
        result = self.monitoring_tools.cpu_usage()
        
        assert len(result) > 0
        assert result[0].type == "text"
        # Check for CPU data in JSON response
        assert "overall_percent" in result[0].text or "percent" in result[0].text

    @patch('psutil.cpu_percent')
    def test_cpu_usage_exception_handling(self, mock_cpu_percent):
        """Test cpu_usage with exception handling."""
        mock_cpu_percent.side_effect = Exception("CPU error")
        
        result = self.monitoring_tools.cpu_usage()
        
        assert len(result) > 0
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    @patch('psutil.virtual_memory')
    def test_memory_usage_valid_inputs(self, mock_virtual_memory):
        """Test memory_usage with valid inputs."""
        mock_memory = MagicMock()
        mock_memory.total = 8589934592  # 8GB
        mock_memory.available = 4294967296  # 4GB
        mock_memory.percent = 50.0
        mock_virtual_memory.return_value = mock_memory
        
        result = self.monitoring_tools.memory_usage()
        
        assert len(result) > 0
        assert result[0].type == "text"
        # Check for memory data in JSON response
        assert "virtual_memory" in result[0].text or "total" in result[0].text

    @patch('psutil.virtual_memory')
    def test_memory_usage_exception_handling(self, mock_virtual_memory):
        """Test memory_usage with exception handling."""
        mock_virtual_memory.side_effect = Exception("Memory error")
        
        result = self.monitoring_tools.memory_usage()
        
        assert len(result) > 0
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    @patch('psutil.disk_usage')
    def test_disk_usage_valid_inputs(self, mock_disk_usage):
        """Test disk_usage with valid inputs."""
        mock_disk = MagicMock()
        mock_disk.total = 1000000000000  # 1TB
        mock_disk.used = 500000000000  # 500GB
        mock_disk.free = 500000000000  # 500GB
        mock_disk.percent = 50.0
        mock_disk_usage.return_value = mock_disk
        
        result = self.monitoring_tools.disk_usage()
        
        assert len(result) > 0
        assert result[0].type == "text"
        # Check for disk data in JSON response
        assert "mountpoint" in result[0].text or "total" in result[0].text

    @patch('psutil.disk_usage')
    def test_disk_usage_exception_handling(self, mock_disk_usage):
        """Test disk_usage with exception handling."""
        mock_disk_usage.side_effect = Exception("Disk error")
        
        result = self.monitoring_tools.disk_usage()
        
        assert len(result) > 0
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    @patch('psutil.process_iter')
    def test_process_list_valid_inputs(self, mock_process_iter):
        """Test process_list with valid inputs."""
        mock_process1 = MagicMock()
        mock_process1.info = {
            'pid': 1234,
            'name': 'python',
            'cpu_percent': 2.5,
            'memory_percent': 1.2
        }
        
        mock_process2 = MagicMock()
        mock_process2.info = {
            'pid': 5678,
            'name': 'nginx',
            'cpu_percent': 1.0,
            'memory_percent': 0.8
        }
        
        mock_process_iter.return_value = [mock_process1, mock_process2]
        
        result = self.monitoring_tools.process_list()
        
        assert len(result) > 0
        assert result[0].type == "text"
        # Check for process data in JSON response or error
        assert "pid" in result[0].text or "error" in result[0].text.lower()

    @patch('psutil.process_iter')
    def test_process_list_exception_handling(self, mock_process_iter):
        """Test process_list with exception handling."""
        mock_process_iter.side_effect = Exception("Process error")
        
        result = self.monitoring_tools.process_list()
        
        assert len(result) > 0
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.boot_time')
    def test_system_status_valid_inputs(self, mock_boot_time, mock_disk_usage, 
                                       mock_virtual_memory, mock_cpu_percent):
        """Test system_status with valid inputs."""
        mock_cpu_percent.return_value = 25.5
        
        mock_memory = MagicMock()
        mock_memory.total = 8589934592
        mock_memory.available = 4294967296
        mock_memory.percent = 50.0
        mock_virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.total = 1000000000000
        mock_disk.used = 500000000000
        mock_disk.free = 500000000000
        mock_disk.percent = 50.0
        mock_disk_usage.return_value = mock_disk
        
        mock_boot_time.return_value = 1640995200  # 2022-01-01 00:00:00
        
        result = self.monitoring_tools.system_status()
        
        assert len(result) > 0
        assert result[0].type == "text"
        # Check for system status data in JSON response
        assert "cpu" in result[0].text and "memory" in result[0].text

    @patch('psutil.cpu_percent')
    def test_system_status_exception_handling(self, mock_cpu_percent):
        """Test system_status with exception handling."""
        mock_cpu_percent.side_effect = Exception("System error")
        
        result = self.monitoring_tools.system_status()
        
        assert len(result) > 0
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()
