"""
Output parser for NetOps MCP.

This module provides utilities for parsing output from various system tools
and converting them into structured data.
"""

import re
from typing import Any, Dict, List, Optional


class OutputParser:
    """Parses output from various system tools."""
    
    @staticmethod
    def parse_ping_output(output: str) -> Dict[str, Any]:
        """Parse ping command output.
        
        Args:
            output: Raw ping output
            
        Returns:
            Dictionary with parsed ping statistics
        """
        stats = {
            "packets_transmitted": 0,
            "packets_received": 0,
            "packet_loss_percent": 0,
            "min_rtt": 0,
            "avg_rtt": 0,
            "max_rtt": 0,
            "mdev_rtt": 0
        }
        
        lines = output.split('\n')
        for line in lines:
            if 'packets transmitted' in line:
                match = re.search(r'(\d+) packets transmitted, (\d+) received', line)
                if match:
                    stats["packets_transmitted"] = int(match.group(1))
                    stats["packets_received"] = int(match.group(2))
                    if stats["packets_transmitted"] > 0:
                        stats["packet_loss_percent"] = 100 - (stats["packets_received"] / stats["packets_transmitted"] * 100)
            
            elif 'rtt min/avg/max/mdev' in line:
                match = re.search(r'(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*)', line)
                if match:
                    stats["min_rtt"] = float(match.group(1))
                    stats["avg_rtt"] = float(match.group(2))
                    stats["max_rtt"] = float(match.group(3))
                    stats["mdev_rtt"] = float(match.group(4))
        
        return stats
    
    @staticmethod
    def parse_traceroute_output(output: str) -> List[Dict[str, Any]]:
        """Parse traceroute command output.
        
        Args:
            output: Raw traceroute output
            
        Returns:
            List of hop information
        """
        hops = []
        lines = output.split('\n')
        
        for line in lines:
            if line.strip() and not line.startswith('traceroute'):
                parts = line.split()
                if len(parts) >= 4:
                    hop_info = {
                        "hop_number": int(parts[0]),
                        "host": parts[1],
                        "ip": parts[1],
                        "times": []
                    }
                    
                    # Extract response times
                    for part in parts[2:]:
                        if part != '*':
                            try:
                                hop_info["times"].append(float(part))
                            except ValueError:
                                pass
                    
                    hops.append(hop_info)
        
        return hops
    
    @staticmethod
    def parse_mtr_output(output: str) -> Dict[str, Any]:
        """Parse mtr command output.
        
        Args:
            output: Raw mtr output
            
        Returns:
            Dictionary with mtr statistics
        """
        stats = {
            "target": "",
            "hops": []
        }
        
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('Start') or line.startswith('HOST:'):
                continue
                
            parts = line.split()
            if len(parts) >= 8:
                try:
                    # Skip header lines and non-numeric entries
                    hop_num = int(parts[0])
                    hop_info = {
                        "hop": hop_num,
                        "host": parts[1],
                        "loss_percent": float(parts[2].rstrip('%')),
                        "snt": int(parts[3]),
                        "last": float(parts[4]),
                        "avg": float(parts[5]),
                        "best": float(parts[6]),
                        "worst": float(parts[7])
                    }
                    stats["hops"].append(hop_info)
                except (ValueError, IndexError):
                    # Skip malformed lines
                    continue
        
        return stats
    
    @staticmethod
    def parse_ss_output(output: str) -> List[Dict[str, Any]]:
        """Parse ss command output.
        
        Args:
            output: Raw ss output
            
        Returns:
            List of connection information
        """
        connections = []
        lines = output.split('\n')
        
        for line in lines:
            if line.strip() and not line.startswith('State'):
                parts = line.split()
                if len(parts) >= 4:
                    conn_info = {
                        "state": parts[0],
                        "recv_q": parts[1],
                        "send_q": parts[2],
                        "local_address": parts[3],
                        "peer_address": parts[4] if len(parts) > 4 else ""
                    }
                    connections.append(conn_info)
        
        return connections
    
    @staticmethod
    def parse_netstat_output(output: str) -> List[Dict[str, Any]]:
        """Parse netstat command output.
        
        Args:
            output: Raw netstat output
            
        Returns:
            List of connection information
        """
        connections = []
        lines = output.split('\n')
        
        for line in lines:
            if line.strip() and not line.startswith('Proto'):
                parts = line.split()
                if len(parts) >= 6:
                    conn_info = {
                        "protocol": parts[0],
                        "recv_q": parts[1],
                        "send_q": parts[2],
                        "local_address": parts[3],
                        "foreign_address": parts[4],
                        "state": parts[5]
                    }
                    connections.append(conn_info)
        
        return connections
