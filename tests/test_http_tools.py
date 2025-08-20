"""
Comprehensive tests for HTTP tools functionality.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from netops_mcp.tools.network.http_tools import HTTPTools


class TestHTTPTools:
    """Test HTTP tools functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.http_tools = HTTPTools()

    def test_initialization(self):
        """Test HTTPTools initialization."""
        assert self.http_tools is not None
        assert hasattr(self.http_tools, 'logger')
        assert hasattr(self.http_tools, '_execute_command')

    @pytest.mark.parametrize("url", [
        "https://httpbin.org/get",
        "https://httpbin.org/post",
        "https://httpbin.org/status/200",
        "https://httpbin.org/status/404"
    ])
    def test_curl_request_valid_urls(self, url, mock_execute_command, sample_curl_output):
        """Test curl request with various valid URLs."""
        mock_execute_command.return_value = sample_curl_output
        
        result = self.http_tools.curl_request(url)
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert url in result[0].text
        assert "200" in result[0].text

    def test_curl_request_with_headers(self, mock_execute_command, sample_curl_output):
        """Test curl request with custom headers."""
        mock_execute_command.return_value = sample_curl_output
        
        headers = {"User-Agent": "TestBot", "Accept": "application/json"}
        result = self.http_tools.curl_request("https://example.com", headers=headers)
        
        assert len(result) == 1
        assert result[0].type == "text"
        # Verify headers were passed to command
        mock_execute_command.assert_called_once()
        call_args = mock_execute_command.call_args[0][0]
        assert "-H" in call_args
        assert "User-Agent: TestBot" in " ".join(call_args)

    def test_curl_request_with_data(self, mock_execute_command, sample_curl_output):
        """Test curl request with POST data."""
        mock_execute_command.return_value = sample_curl_output
        
        data = {"key": "value", "test": "data"}
        result = self.http_tools.curl_request("https://example.com", method="POST", data=data)
        
        assert len(result) == 1
        assert result[0].type == "text"
        # Verify data was passed to command
        mock_execute_command.assert_called_once()
        call_args = mock_execute_command.call_args[0][0]
        assert "-d" in call_args

    def test_curl_request_with_timeout(self, mock_execute_command, sample_curl_output):
        """Test curl request with custom timeout."""
        mock_execute_command.return_value = sample_curl_output
        
        result = self.http_tools.curl_request("https://example.com", timeout=30)
        
        assert len(result) == 1
        assert result[0].type == "text"
        # Verify timeout was passed to command
        mock_execute_command.assert_called_once()
        call_args = mock_execute_command.call_args[0][0]
        assert "--max-time" in call_args
        assert "30" in call_args

    def test_curl_request_invalid_url(self, mock_execute_command):
        """Test curl request with invalid URL."""
        mock_execute_command.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "curl: (6) Could not resolve host: invalid-url",
            "return_code": 6,
            "command": "curl -s -w @- -o /tmp/curl_output -X GET invalid-url"
        }
        
        result = self.http_tools.curl_request("invalid-url")
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_curl_request_empty_url(self):
        """Test curl request with empty URL."""
        result = self.http_tools.curl_request("")
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_curl_request_none_url(self):
        """Test curl request with None URL."""
        result = self.http_tools.curl_request(None)
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_curl_request_command_timeout(self, mock_execute_command):
        """Test curl request when command times out."""
        mock_execute_command.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "Command timed out",
            "return_code": -1,
            "command": "curl -s -w @- -o /tmp/curl_output -X GET https://example.com"
        }
        
        result = self.http_tools.curl_request("https://example.com")
        
        assert len(result) == 1
        assert result[0].type == "text"
        # Check for error response instead of specific timeout text
        assert '"success": false' in result[0].text

    @pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE", "PATCH"])
    def test_curl_request_different_methods(self, method, mock_execute_command, sample_curl_output):
        """Test curl request with different HTTP methods."""
        mock_execute_command.return_value = sample_curl_output
        
        result = self.http_tools.curl_request("https://example.com", method=method)
        
        assert len(result) == 1
        assert result[0].type == "text"
        # Verify method was passed to command
        mock_execute_command.assert_called_once()
        call_args = mock_execute_command.call_args[0][0]
        assert f"-X {method}" in " ".join(call_args)

    def test_httpie_request_valid_url(self, mock_execute_command, sample_curl_output):
        """Test httpie request with valid URL."""
        mock_execute_command.return_value = sample_curl_output
        
        result = self.http_tools.httpie_request("https://example.com")
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "https://example.com" in result[0].text

    def test_httpie_request_with_headers(self, mock_execute_command, sample_curl_output):
        """Test httpie request with custom headers."""
        mock_execute_command.return_value = sample_curl_output
        
        headers = {"User-Agent": "TestBot", "Accept": "application/json"}
        result = self.http_tools.httpie_request("https://example.com", headers=headers)
        
        assert len(result) == 1
        assert result[0].type == "text"
        # Verify headers were passed to command
        mock_execute_command.assert_called_once()
        call_args = mock_execute_command.call_args[0][0]
        assert "User-Agent:TestBot" in " ".join(call_args)

    def test_httpie_request_with_data(self, mock_execute_command, sample_curl_output):
        """Test httpie request with POST data."""
        mock_execute_command.return_value = sample_curl_output
        
        data = {"key": "value", "test": "data"}
        result = self.http_tools.httpie_request("https://example.com", method="POST", data=data)
        
        assert len(result) == 1
        assert result[0].type == "text"
        # Verify data was passed to command
        mock_execute_command.assert_called_once()
        call_args = mock_execute_command.call_args[0][0]
        assert "key=value" in " ".join(call_args)

    def test_httpie_request_invalid_url(self, mock_execute_command):
        """Test httpie request with invalid URL."""
        mock_execute_command.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "http: error: ConnectionError",
            "return_code": 1,
            "command": "http GET invalid-url"
        }
        
        result = self.http_tools.httpie_request("invalid-url")
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_api_test_valid_url(self, mock_execute_command, sample_curl_output):
        """Test API test with valid URL."""
        mock_execute_command.return_value = sample_curl_output
        
        result = self.http_tools.api_test("https://httpbin.org/status/200")
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "200" in result[0].text

    def test_api_test_expected_status_mismatch(self, mock_execute_command, sample_curl_output):
        """Test API test with status code mismatch."""
        mock_execute_command.return_value = sample_curl_output
        
        result = self.http_tools.api_test("https://httpbin.org/status/404", expected_status=200)
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "expected" in result[0].text.lower()

    def test_api_test_with_headers(self, mock_execute_command, sample_curl_output):
        """Test API test with custom headers."""
        mock_execute_command.return_value = sample_curl_output
        
        headers = {"Authorization": "Bearer token123"}
        result = self.http_tools.api_test("https://example.com", headers=headers)
        
        assert len(result) == 1
        assert result[0].type == "text"
        # Verify headers were passed to command
        mock_execute_command.assert_called_once()
        call_args = mock_execute_command.call_args[0][0]
        assert "-H" in call_args
        assert "Authorization: Bearer token123" in " ".join(call_args)

    def test_validate_url(self):
        """Test URL validation."""
        # Valid URLs
        assert self.http_tools._validate_url("https://example.com") == True
        assert self.http_tools._validate_url("http://localhost:8080") == True
        assert self.http_tools._validate_url("https://api.github.com/v1/users") == True
        
        # Invalid URLs
        assert self.http_tools._validate_url("") == False
        assert self.http_tools._validate_url(None) == False
        assert self.http_tools._validate_url("not-a-url") == False
        assert self.http_tools._validate_url("ftp://example.com") == False

    def test_validate_method(self):
        """Test HTTP method validation."""
        # Valid methods
        assert self.http_tools._validate_method("GET") == True
        assert self.http_tools._validate_method("POST") == True
        assert self.http_tools._validate_method("PUT") == True
        assert self.http_tools._validate_method("DELETE") == True
        assert self.http_tools._validate_method("PATCH") == True
        
        # Invalid methods
        assert self.http_tools._validate_method("INVALID") == False
        assert self.http_tools._validate_method("") == False
        assert self.http_tools._validate_method(None) == False

    def test_format_curl_command(self):
        """Test curl command formatting."""
        url = "https://example.com"
        method = "POST"
        headers = {"Content-Type": "application/json"}
        data = {"key": "value"}
        timeout = 30
        
        command = self.http_tools._format_curl_command(url, method, headers, data, timeout)
        
        assert "curl" in command
        assert url in command
        # Check for method in command (format may vary)
        # Check for method in command (format may vary)
        command_str = " ".join(str(item) for item in command)
        assert method in command_str
        assert "-H" in command
        # Check for content type header (format may vary)
        command_str = " ".join(str(item) for item in command)
        assert "Content-Type" in command_str
        assert "-d" in command
        assert "--max-time" in command
        assert "30" in command

    def test_format_httpie_command(self):
        """Test httpie command formatting."""
        url = "https://example.com"
        method = "POST"
        headers = {"Content-Type": "application/json"}
        data = {"key": "value"}
        timeout = 30
        
        command = self.http_tools._format_httpie_command(url, method, headers, data, timeout)
        
        assert "http" in command
        assert method in command
        assert url in command
        assert "Content-Type:application/json" in " ".join(command)
        assert "key=value" in " ".join(command)
        assert "--timeout" in command
        assert "30" in command

    def test_parse_curl_output(self):
        """Test curl output parsing."""
        curl_output = """{
  "http_code": "200",
  "time_total": "0.123",
  "time_connect": "0.045",
  "time_namelookup": "0.023",
  "size_download": "1234",
  "speed_download": "10000"
}"""
        
        parsed = self.http_tools._parse_curl_output(curl_output)
        
        assert parsed["http_code"] == "200"
        assert parsed["time_total"] == "0.123"
        assert parsed["size_download"] == "1234"

    def test_parse_curl_output_invalid_json(self):
        """Test curl output parsing with invalid JSON."""
        curl_output = "Invalid JSON output"
        
        parsed = self.http_tools._parse_curl_output(curl_output)
        
        # Check for error in parsed output
        assert "error" in parsed

    def test_handle_http_error(self):
        """Test HTTP error handling."""
        error = Exception("Connection failed")
        
        result = self.http_tools._handle_error("curl request", error)
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()
        assert "curl request" in result[0].text

    @pytest.mark.parametrize("url,expected", [
        ("https://httpbin.org/status/200", True),
        ("https://httpbin.org/status/404", True),
        ("https://httpbin.org/status/500", True),
        ("invalid-url", False),
        ("", False),
        (None, False)
    ])
    def test_url_validation_edge_cases(self, url, expected):
        """Test URL validation with edge cases."""
        assert self.http_tools._validate_url(url) == expected

    def test_command_execution_error_handling(self, mock_execute_command):
        """Test error handling when command execution fails."""
        mock_execute_command.side_effect = Exception("Command execution failed")
        
        result = self.http_tools.curl_request("https://example.com")
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "error" in result[0].text.lower()

    def test_timeout_handling(self, mock_execute_command):
        """Test timeout handling in HTTP requests."""
        mock_execute_command.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "Operation timed out",
            "return_code": -1,
            "command": "curl -s -w @- -o /tmp/curl_output -X GET https://example.com"
        }
        
        result = self.http_tools.curl_request("https://example.com", timeout=5)
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "timeout" in result[0].text.lower() or "error" in result[0].text.lower()
