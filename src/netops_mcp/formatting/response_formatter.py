"""
Response formatter for NetOps MCP.

This module provides utilities for formatting responses from various tools
into standardized formats.
"""

import json
from typing import Any, Dict, List, Optional
from mcp.types import TextContent as Content


class ResponseFormatter:
    """Formats tool responses into standardized MCP content."""
    
    @staticmethod
    def format_json_response(data: Any, tool_name: Optional[str] = None) -> List[Content]:
        """Format data as JSON response.
        
        Args:
            data: Data to format
            tool_name: Name of the tool for context
            
        Returns:
            List of Content objects
        """
        if isinstance(data, dict):
            formatted = json.dumps(data, indent=2, default=str)
        elif isinstance(data, list):
            formatted = json.dumps(data, indent=2, default=str)
        else:
            formatted = str(data)
            
        return [Content(type="text", text=formatted)]
    
    @staticmethod
    def format_table_response(data: List[Dict[str, Any]], headers: Optional[List[str]] = None) -> List[Content]:
        """Format data as table response.
        
        Args:
            data: List of dictionaries to format as table
            headers: Optional list of headers
            
        Returns:
            List of Content objects
        """
        if not data:
            return [Content(type="text", text="No data available")]
        
        if not headers:
            headers = list(data[0].keys())
        
        # Create table header
        table = "| " + " | ".join(headers) + " |\n"
        table += "|" + "|".join(["---"] * len(headers)) + "|\n"
        
        # Add data rows
        for row in data:
            values = [str(row.get(header, "")) for header in headers]
            table += "| " + " | ".join(values) + " |\n"
        
        return [Content(type="text", text=table)]
    
    @staticmethod
    def format_error_response(error: Exception, operation: str) -> List[Content]:
        """Format error response.
        
        Args:
            error: Exception that occurred
            operation: Description of the operation that failed
            
        Returns:
            List of Content objects
        """
        error_data = {
            "error": True,
            "operation": operation,
            "message": str(error),
            "type": type(error).__name__
        }
        
        return ResponseFormatter.format_json_response(error_data)
    
    @staticmethod
    def format_success_response(data: Any, operation: str) -> List[Content]:
        """Format success response.
        
        Args:
            data: Data to include in response
            operation: Description of the operation
            
        Returns:
            List of Content objects
        """
        success_data = {
            "success": True,
            "operation": operation,
            "data": data
        }
        
        return ResponseFormatter.format_json_response(success_data)
