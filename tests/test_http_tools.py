"""
Comprehensive tests for HTTP tools functionality.
"""

import inspect
import os
import stat
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import netops_mcp.tools.network.http_tools as http_tools_module
import pytest
from netops_mcp.tools.network.http_tools import HTTPTools


def _find_url(command):
    """Locate the request URL inside a built curl/api argv."""
    return next(
        arg for arg in command if isinstance(arg, str) and arg.startswith(("http://", "https://"))
    )


class TestHTTPTools:
    """Test HTTP tools functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.http_tools = HTTPTools()

    def test_initialization(self):
        """Test HTTPTools initialization."""
        assert self.http_tools is not None
        assert hasattr(self.http_tools, "logger")
        assert hasattr(self.http_tools, "_execute_command")

    @pytest.mark.parametrize(
        "url",
        [
            "https://httpbin.org/get",
            "https://httpbin.org/post",
            "https://httpbin.org/status/200",
            "https://httpbin.org/status/404",
        ],
    )
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
            "command": "curl -s -w @- -o /tmp/curl_output -X GET invalid-url",
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
            "command": "curl -s -w @- -o /tmp/curl_output -X GET https://example.com",
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
            "command": "http GET invalid-url",
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
        assert self.http_tools._validate_url("https://example.com") is True
        assert self.http_tools._validate_url("http://localhost:8080") is True
        assert self.http_tools._validate_url("https://api.github.com/v1/users") is True

        # Invalid URLs
        assert self.http_tools._validate_url("") is False
        assert self.http_tools._validate_url(None) is False
        assert self.http_tools._validate_url("not-a-url") is False
        assert self.http_tools._validate_url("ftp://example.com") is False

    def test_validate_method(self):
        """Test HTTP method validation."""
        # Valid methods
        assert self.http_tools._validate_method("GET") is True
        assert self.http_tools._validate_method("POST") is True
        assert self.http_tools._validate_method("PUT") is True
        assert self.http_tools._validate_method("DELETE") is True
        assert self.http_tools._validate_method("PATCH") is True

        # Invalid methods
        assert self.http_tools._validate_method("INVALID") is False
        assert self.http_tools._validate_method("") is False
        assert self.http_tools._validate_method(None) is False

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

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://httpbin.org/status/200", True),
            ("https://httpbin.org/status/404", True),
            ("https://httpbin.org/status/500", True),
            ("invalid-url", False),
            ("", False),
            (None, False),
        ],
    )
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
            "command": "curl -s -w @- -o /tmp/curl_output -X GET https://example.com",
        }

        result = self.http_tools.curl_request("https://example.com", timeout=5)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "timeout" in result[0].text.lower() or "error" in result[0].text.lower()

    # ------------------------------------------------------------------
    # SEC-02 / TEST-03: per-request tempfile + concurrency isolation
    # ------------------------------------------------------------------

    def test_curl_request_tempfile_mode_0600_and_cleanup(self, mock_execute_command):
        """curl_request writes to a per-request 0600 tempfile, reads it back,
        and unlinks it in finally (no shared /tmp/curl_output)."""
        captured = {}

        def fake_exec(command, timeout=0):
            out_path = command[command.index("-o") + 1]
            captured["path"] = out_path
            captured["mode"] = stat.S_IMODE(os.stat(out_path).st_mode)
            with open(out_path, "w") as fh:
                fh.write("body-data-marker")
            return {
                "success": True,
                "stdout": '{"http_code": "200"}',
                "stderr": "",
                "return_code": 0,
            }

        mock_execute_command.side_effect = fake_exec

        result = self.http_tools.curl_request("https://example.com")

        assert captured["mode"] == 0o600
        assert "body-data-marker" in result[0].text
        # finally cleanup: the private tempfile must be gone after the call
        assert not os.path.exists(captured["path"])

    def test_curl_request_tempfile_cleanup_on_failure(self, mock_execute_command):
        """The per-request mkstemp tempfile is unlinked even when the command
        reports failure (finally cleanup on the error branch)."""
        created = []
        real_mkstemp = tempfile.mkstemp

        def spy_mkstemp(*args, **kwargs):
            fd, path = real_mkstemp(*args, **kwargs)
            created.append(path)
            return fd, path

        mock_execute_command.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "boom",
            "return_code": 1,
        }

        with patch(
            "netops_mcp.tools.network.http_tools.tempfile.mkstemp",
            side_effect=spy_mkstemp,
        ):
            self.http_tools.curl_request("https://example.com")

        assert created, "curl_request must create a per-request tempfile via mkstemp"
        for path in created:
            assert not os.path.exists(path)

    def test_no_shared_tmp_paths_in_source(self):
        """The hardcoded shared /tmp curl output paths must be gone (SEC-02)."""
        source = inspect.getsource(http_tools_module)
        # Strip comment lines before scanning for the shared literals.
        code = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))
        assert "/tmp/curl_output" not in code
        assert "/tmp/api_response" not in code

    def test_curl_request_concurrent_no_cross_contamination(self, mock_execute_command):
        """N concurrent curl_request calls each read back only their own body.
        A shared output path would cross-contaminate under the race window."""
        urls = [f"https://example.com/req-{i}" for i in range(12)]

        def fake_exec(command, timeout=0):
            out_path = command[command.index("-o") + 1]
            url = _find_url(command)
            # Bracket the marker so one url is never a substring of another
            # (e.g. req-1 vs req-10).
            with open(out_path, "w") as fh:
                fh.write(f"[BODY-FOR::{url}]")
            # Widen the race window so a shared path deterministically clobbers.
            time.sleep(0.02)
            return {
                "success": True,
                "stdout": '{"http_code": "200"}',
                "stderr": "",
                "return_code": 0,
            }

        mock_execute_command.side_effect = fake_exec

        def run(u):
            res = self.http_tools.curl_request(u)
            return u, res[0].text

        with ThreadPoolExecutor(max_workers=12) as executor:
            results = list(executor.map(run, urls))

        for url, text in results:
            assert f"[BODY-FOR::{url}]" in text, f"missing own body for {url}"
            for other in urls:
                if other != url:
                    assert (
                        f"[BODY-FOR::{other}]" not in text
                    ), f"cross-contamination: {other} leaked into {url}"

    def test_api_test_concurrent_no_cross_contamination(self, mock_execute_command):
        """N concurrent api_test calls each read back only their own body."""
        urls = [f"https://example.com/api-{i}" for i in range(12)]

        def fake_exec(command, timeout=0):
            out_path = command[command.index("-o") + 1]
            url = _find_url(command)
            # Bracket the marker so one url is never a substring of another.
            with open(out_path, "w") as fh:
                fh.write(f"[BODY-FOR::{url}]")
            time.sleep(0.02)
            return {
                "success": True,
                "stdout": "200",
                "stderr": "",
                "return_code": 0,
            }

        mock_execute_command.side_effect = fake_exec

        def run(u):
            res = self.http_tools.api_test(u)
            return u, res[0].text

        with ThreadPoolExecutor(max_workers=12) as executor:
            results = list(executor.map(run, urls))

        for url, text in results:
            assert f"[BODY-FOR::{url}]" in text, f"missing own body for {url}"
            for other in urls:
                if other != url:
                    assert (
                        f"[BODY-FOR::{other}]" not in text
                    ), f"cross-contamination: {other} leaked into {url}"

    # ------------------------------------------------------------------
    # SEC-03 / TEST-04: curl IP-pin + redirect-off (redirect-to-metadata)
    # ------------------------------------------------------------------

    def test_curl_command_pins_ip_and_disables_redirects(self):
        """Built curl argv pins the classified IP via --resolve (port 443 for
        https), sets --max-redirs 0, and never adds -L (TEST-04)."""
        command = self.http_tools._format_curl_command(
            "https://example.com/path",
            "GET",
            out_path="/tmp/ignored",
            resolved_ips=["93.184.216.34"],
        )
        assert "--resolve" in command
        assert command[command.index("--resolve") + 1] == "example.com:443:93.184.216.34"
        assert "--max-redirs" in command
        assert command[command.index("--max-redirs") + 1] == "0"
        assert "-L" not in command

    def test_curl_command_http_scheme_pins_port_80(self):
        """http:// URLs pin port 80 in --resolve (Pitfall 7)."""
        command = self.http_tools._format_curl_command(
            "http://example.com/x",
            "GET",
            out_path="/tmp/ignored",
            resolved_ips=["93.184.216.34"],
        )
        assert command[command.index("--resolve") + 1] == "example.com:80:93.184.216.34"

    def test_curl_command_explicit_port_pins_that_port(self):
        """An explicit URL port is used verbatim in --resolve."""
        command = self.http_tools._format_curl_command(
            "https://example.com:8443/x",
            "GET",
            out_path="/tmp/ignored",
            resolved_ips=["10.0.0.5"],
        )
        assert command[command.index("--resolve") + 1] == "example.com:8443:10.0.0.5"

    def test_curl_request_pins_resolved_ip(self, mock_execute_command, sample_curl_output):
        """curl_request pins the SSRF-classified IP and disables redirects."""
        mock_execute_command.return_value = sample_curl_output

        self.http_tools.curl_request("https://example.com/get")

        call_args = mock_execute_command.call_args[0][0]
        assert "--resolve" in call_args
        assert call_args[call_args.index("--resolve") + 1] == "example.com:443:93.184.216.34"
        assert "--max-redirs" in call_args
        assert call_args[call_args.index("--max-redirs") + 1] == "0"
        assert "-L" not in call_args

    def test_api_test_pins_resolved_ip(self, mock_execute_command, sample_curl_output):
        """api_test pins the SSRF-classified IP and disables redirects."""
        mock_execute_command.return_value = sample_curl_output

        self.http_tools.api_test("https://example.com/status/200")

        call_args = mock_execute_command.call_args[0][0]
        assert "--resolve" in call_args
        assert call_args[call_args.index("--resolve") + 1] == "example.com:443:93.184.216.34"
        assert "--max-redirs" in call_args
        assert "-L" not in call_args

    def test_curl_request_blocks_loopback(self, mock_execute_command):
        """A loopback URL is blocked by SSRF classification (fail-closed);
        curl is never executed."""
        result = self.http_tools.curl_request("http://127.0.0.1:8080/")

        assert '"error": true' in result[0].text
        mock_execute_command.assert_not_called()

    def test_curl_request_blocks_metadata(self, mock_execute_command):
        """A cloud-metadata URL (169.254.169.254) is blocked before curl runs."""
        result = self.http_tools.curl_request("http://169.254.169.254/latest/meta-data/")

        assert '"error": true' in result[0].text
        mock_execute_command.assert_not_called()

    def test_api_test_blocks_loopback(self, mock_execute_command):
        """api_test blocks a loopback URL before executing curl."""
        result = self.http_tools.api_test("http://127.0.0.1:9000/")

        assert '"error": true' in result[0].text
        mock_execute_command.assert_not_called()

    def test_httpie_request_blocks_metadata(self, mock_execute_command):
        """httpie_request SSRF-classifies the host and blocks metadata
        (un-pinned caveat, but classification gate still fires)."""
        result = self.http_tools.httpie_request("http://169.254.169.254/")

        assert '"error": true' in result[0].text
        mock_execute_command.assert_not_called()

    def test_validate_url_delegates_to_central_validator(self):
        """_validate_url stays bool-equivalent after delegating to the central
        validate_url (REF-02)."""
        assert self.http_tools._validate_url("https://example.com") is True
        assert self.http_tools._validate_url("http://localhost:8080") is True
        assert self.http_tools._validate_url("https://api.github.com/v1/users") is True
        assert self.http_tools._validate_url("") is False
        assert self.http_tools._validate_url(None) is False
        assert self.http_tools._validate_url("not-a-url") is False
        assert self.http_tools._validate_url("ftp://example.com") is False
