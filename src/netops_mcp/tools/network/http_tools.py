"""
HTTP/API testing tools for DevOps MCP.
"""

import json
from typing import Dict, List, Optional, Any
from mcp.types import TextContent as Content
from ..base import DevOpsTool


class HTTPTools(DevOpsTool):
    """Tools for HTTP/API testing and diagnostics."""

    def curl_request(self, url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None, 
                    data: Optional[str] = None, timeout: int = 30) -> List[Content]:
        """Execute HTTP request using curl.

        Args:
            url: Target URL
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            headers: Optional HTTP headers
            data: Optional request body
            timeout: Request timeout in seconds

        Returns:
            List of Content objects with curl response
        """
        try:
            if not self._validate_host(url):
                raise ValueError("Invalid URL provided")

            command = ['curl', '-s', '-w', '@-', '-o', '/tmp/curl_output', '-X', method, url]
            
            # Add headers
            if headers:
                for key, value in headers.items():
                    command.extend(['-H', f'{key}: {value}'])
            
            # Add data
            if data:
                command.extend(['-d', data])
            
            # Add timeout
            command.extend(['--max-time', str(timeout)])
            
            # Custom format string for curl
            format_string = (
                '{"http_code": "%{http_code}", '
                '"time_total": "%{time_total}", '
                '"time_connect": "%{time_connect}", '
                '"time_namelookup": "%{time_namelookup}", '
                '"size_download": "%{size_download}", '
                '"speed_download": "%{speed_download}"}'
            )
            
            # Execute curl with format
            result = self._execute_command(command, timeout + 5)
            
            if result["success"]:
                # Read output file
                try:
                    with open('/tmp/curl_output', 'r') as f:
                        response_body = f.read()
                except FileNotFoundError:
                    response_body = ""
                
                # Parse curl stats
                try:
                    stats = json.loads(result["stdout"])
                except json.JSONDecodeError:
                    stats = {"error": "Could not parse curl stats"}
                
                response_data = {
                    "url": url,
                    "method": method,
                    "success": True,
                    "stats": stats,
                    "response_body": response_body,
                    "stderr": result["stderr"]
                }
            else:
                response_data = {
                    "url": url,
                    "method": method,
                    "success": False,
                    "error": result["stderr"],
                    "return_code": result["return_code"]
                }
            
            return self._format_response(response_data, "curl_request")
            
        except Exception as e:
            return self._handle_error("curl request", e)

    def httpie_request(self, url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None,
                      data: Optional[Dict[str, Any]] = None, timeout: int = 30) -> List[Content]:
        """Execute HTTP request using httpie.

        Args:
            url: Target URL
            method: HTTP method
            headers: Optional HTTP headers
            data: Optional request body
            timeout: Request timeout in seconds

        Returns:
            List of Content objects with httpie response
        """
        try:
            if not self._validate_host(url):
                raise ValueError("Invalid URL provided")

            command = ['http', method, url, '--timeout', str(timeout)]
            
            # Add headers
            if headers:
                for key, value in headers.items():
                    command.extend([f'{key}:{value}'])
            
            # Add data
            if data:
                for key, value in data.items():
                    command.extend([f'{key}={value}'])
            
            result = self._execute_command(command, timeout + 5)
            
            response_data = {
                "url": url,
                "method": method,
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "return_code": result["return_code"]
            }
            
            return self._format_response(response_data, "httpie_request")
            
        except Exception as e:
            return self._handle_error("httpie request", e)

    def api_test(self, url: str, method: str = "GET", expected_status: int = 200,
                headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> List[Content]:
        """Test API endpoint with validation.

        Args:
            url: API endpoint URL
            method: HTTP method
            expected_status: Expected HTTP status code
            headers: Optional HTTP headers
            timeout: Request timeout

        Returns:
            List of Content objects with API test results
        """
        try:
            if not self._validate_host(url):
                raise ValueError("Invalid URL provided")

            # Use curl for API testing
            command = ['curl', '-s', '-w', '%{http_code}', '-o', '/tmp/api_response', '-X', method, url]
            
            # Add headers
            if headers:
                for key, value in headers.items():
                    command.extend(['-H', f'{key}: {value}'])
            
            # Add timeout
            command.extend(['--max-time', str(timeout)])
            
            result = self._execute_command(command, timeout + 5)
            
            if result["success"]:
                # Read response body
                try:
                    with open('/tmp/api_response', 'r') as f:
                        response_body = f.read()
                except FileNotFoundError:
                    response_body = ""
                
                # Parse status code
                try:
                    status_code = int(result["stdout"])
                except ValueError:
                    status_code = 0
                
                test_result = {
                    "url": url,
                    "method": method,
                    "expected_status": expected_status,
                    "actual_status": status_code,
                    "success": status_code == expected_status,
                    "response_body": response_body,
                    "test_passed": status_code == expected_status
                }
            else:
                test_result = {
                    "url": url,
                    "method": method,
                    "expected_status": expected_status,
                    "success": False,
                    "error": result["stderr"],
                    "test_passed": False
                }
            
            return self._format_response(test_result, "api_test")
            
        except Exception as e:
            return self._handle_error("API test", e)
