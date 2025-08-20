"""
Data converter for NetOps MCP.

This module provides utilities for converting data between different formats
and units.
"""

from typing import Any, Dict, List, Union


class DataConverter:
    """Converts data between different formats and units."""
    
    @staticmethod
    def bytes_to_human_readable(bytes_value: int) -> str:
        """Convert bytes to human readable format.
        
        Args:
            bytes_value: Number of bytes
            
        Returns:
            Human readable string (e.g., "1.5 MB")
        """
        if bytes_value == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        unit_index = 0
        
        while bytes_value >= 1024 and unit_index < len(units) - 1:
            bytes_value /= 1024
            unit_index += 1
        
        return f"{bytes_value:.1f} {units[unit_index]}"
    
    @staticmethod
    def seconds_to_human_readable(seconds: float) -> str:
        """Convert seconds to human readable format.
        
        Args:
            seconds: Number of seconds
            
        Returns:
            Human readable string (e.g., "1.5s", "2m 30s")
        """
        if seconds < 1:
            return f"{seconds*1000:.1f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds:.1f}s"
        else:
            hours = int(seconds // 3600)
            remaining_minutes = int((seconds % 3600) // 60)
            return f"{hours}h {remaining_minutes}m"
    
    @staticmethod
    def dict_to_table(data: List[Dict[str, Any]]) -> str:
        """Convert list of dictionaries to table format.
        
        Args:
            data: List of dictionaries
            
        Returns:
            Table formatted string
        """
        if not data:
            return "No data available"
        
        headers = list(data[0].keys())
        table = "| " + " | ".join(headers) + " |\n"
        table += "|" + "|".join(["---"] * len(headers)) + "|\n"
        
        for row in data:
            values = [str(row.get(header, "")) for header in headers]
            table += "| " + " | ".join(values) + " |\n"
        
        return table
    
    @staticmethod
    def flatten_dict(data: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary.
        
        Args:
            data: Dictionary to flatten
            parent_key: Parent key for nested items
            sep: Separator for nested keys
            
        Returns:
            Flattened dictionary
        """
        items = []
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(DataConverter.flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    @staticmethod
    def normalize_network_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize network data for consistent formatting.
        
        Args:
            data: Network data to normalize
            
        Returns:
            Normalized data
        """
        normalized = {}
        
        for key, value in data.items():
            if isinstance(value, (int, float)):
                if 'bytes' in key.lower() or 'size' in key.lower():
                    normalized[key] = DataConverter.bytes_to_human_readable(value)
                elif 'time' in key.lower() or 'duration' in key.lower():
                    normalized[key] = DataConverter.seconds_to_human_readable(value)
                else:
                    normalized[key] = value
            else:
                normalized[key] = value
        
        return normalized
    
    @staticmethod
    def convert_boolean_string(value: str) -> bool:
        """Convert string to boolean.
        
        Args:
            value: String value
            
        Returns:
            Boolean value
        """
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'on', 'enabled')
        
        return bool(value)
