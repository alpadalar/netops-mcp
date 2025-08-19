"""
System monitoring tools for DevOps MCP.
"""

import psutil
from typing import Dict, List, Optional
from mcp.types import TextContent as Content
from ..base import DevOpsTool


class MonitoringTools(DevOpsTool):
    """Tools for system monitoring and resource usage."""

    def system_status(self) -> List[Content]:
        """Get system status information.

        Returns:
            List of Content objects with system status
        """
        try:
            # Get system information
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            boot_time = psutil.boot_time()
            
            # Get network interfaces
            network_interfaces = {}
            for interface, stats in psutil.net_io_counters(pernic=True).items():
                network_interfaces[interface] = {
                    "bytes_sent": stats.bytes_sent,
                    "bytes_recv": stats.bytes_recv,
                    "packets_sent": stats.packets_sent,
                    "packets_recv": stats.packets_recv
                }
            
            status_data = {
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count(),
                    "count_logical": psutil.cpu_count(logical=True)
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "boot_time": boot_time,
                "network_interfaces": network_interfaces
            }
            
            return self._format_response(status_data, "system_status")
            
        except Exception as e:
            return self._handle_error("system status", e)

    def cpu_usage(self) -> List[Content]:
        """Get detailed CPU usage information.

        Returns:
            List of Content objects with CPU usage
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
            cpu_freq = psutil.cpu_freq()
            cpu_stats = psutil.cpu_stats()
            
            cpu_data = {
                "overall_percent": psutil.cpu_percent(interval=1),
                "per_cpu_percent": cpu_percent,
                "count": psutil.cpu_count(),
                "count_logical": psutil.cpu_count(logical=True),
                "frequency": {
                    "current": cpu_freq.current if cpu_freq else None,
                    "min": cpu_freq.min if cpu_freq else None,
                    "max": cpu_freq.max if cpu_freq else None
                },
                "stats": {
                    "ctx_switches": cpu_stats.ctx_switches,
                    "interrupts": cpu_stats.interrupts,
                    "soft_interrupts": cpu_stats.soft_interrupts,
                    "syscalls": cpu_stats.syscalls
                }
            }
            
            return self._format_response(cpu_data, "cpu_usage")
            
        except Exception as e:
            return self._handle_error("cpu usage", e)

    def memory_usage(self) -> List[Content]:
        """Get detailed memory usage information.

        Returns:
            List of Content objects with memory usage
        """
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            memory_data = {
                "virtual_memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "free": memory.free,
                    "percent": memory.percent,
                    "active": memory.active,
                    "inactive": memory.inactive,
                    "buffers": memory.buffers,
                    "cached": memory.cached,
                    "shared": memory.shared
                },
                "swap_memory": {
                    "total": swap.total,
                    "used": swap.used,
                    "free": swap.free,
                    "percent": swap.percent,
                    "sin": swap.sin,
                    "sout": swap.sout
                }
            }
            
            return self._format_response(memory_data, "memory_usage")
            
        except Exception as e:
            return self._handle_error("memory usage", e)

    def disk_usage(self) -> List[Content]:
        """Get disk usage information.

        Returns:
            List of Content objects with disk usage
        """
        try:
            disk_partitions = psutil.disk_partitions()
            disk_usage_data = {}
            
            for partition in disk_partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage_data[partition.device] = {
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": (usage.used / usage.total) * 100
                    }
                except PermissionError:
                    # Skip partitions we can't access
                    continue
            
            return self._format_response(disk_usage_data, "disk_usage")
            
        except Exception as e:
            return self._handle_error("disk usage", e)

    def process_list(self, limit: int = 20) -> List[Content]:
        """List running processes.

        Args:
            limit: Number of processes to show

        Returns:
            List of Content objects with process list
        """
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    proc_info = proc.info
                    processes.append({
                        "pid": proc_info['pid'],
                        "name": proc_info['name'],
                        "cpu_percent": proc_info['cpu_percent'],
                        "memory_percent": proc_info['memory_percent'],
                        "status": proc_info['status']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by CPU usage and limit results
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            processes = processes[:limit]
            
            return self._format_response(processes, "process_list")
            
        except Exception as e:
            return self._handle_error("process list", e)
