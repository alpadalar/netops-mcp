"""
Characterization tests for netops_mcp.validators.input_validator (REF-01).

Locks the full behavior corpus from 02-RESEARCH.md "Empirical Baseline" so the
double-escape regex fix cannot loosen any rejection, and encodes the target
contract for dotted hostnames/domains (the *_dotted_accept groups are RED
before the fix and GREEN after it). All other tests pass both before and
after the fix.
"""

import pytest

from netops_mcp.validators.input_validator import (
    ValidationError,
    sanitize_command_arg,
    validate_domain,
    validate_hostname,
    validate_port_range,
    validate_url,
)


class TestValidateHostname:
    """Characterization corpus for validate_hostname."""

    @pytest.mark.parametrize("hostname", [
        "localhost",
        "my-host",
    ])
    def test_hostname_single_label_accept(self, hostname):
        """Single-label hostnames are accepted via the regex path."""
        assert validate_hostname(hostname) == hostname

    @pytest.mark.parametrize("hostname", [
        "192.168.1.1",
        "8.8.8.8",
        "::1",
    ])
    def test_hostname_ip_accept(self, hostname):
        """IP literals pass through the ipaddress branch, not the regex."""
        assert validate_hostname(hostname) == hostname

    @pytest.mark.parametrize("hostname", [
        "example.com",
        "sub.domain.co.uk",
        "xn--nxasmq6b.example",  # punycode label
    ])
    def test_hostname_dotted_accept(self, hostname):
        """Dotted hostnames must be accepted (REF-01 target contract)."""
        assert validate_hostname(hostname) == hostname

    @pytest.mark.parametrize("hostname", [
        "[::1]",  # bracketed form is URL notation, not an IP literal
        "a" * 64,  # 64-char single label exceeds the {1,63} bound
        "host name",  # embedded space cannot match the label charset
        "evil;rm -rf",  # injection chars hit the pre-regex dangerous-char check
        "host..double",  # empty label between dots
        "-badstart",  # leading hyphen (negative lookahead)
        "bad-",  # trailing hyphen (negative lookbehind)
        "example.com.",  # trailing dot leaves a dangling separator
    ])
    def test_hostname_reject(self, hostname):
        """Malformed and injection-bearing hostnames raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_hostname(hostname)


class TestValidateDomain:
    """Characterization corpus for validate_domain."""

    @pytest.mark.parametrize("domain", [
        "internal-host",  # single label allowed for internal networks
    ])
    def test_domain_single_label_accept(self, domain):
        """Single-label domains are accepted via single_label_pattern."""
        assert validate_domain(domain) == domain

    @pytest.mark.parametrize("domain", [
        "example.com",
        "google.com",
        "sub.domain.co.uk",
    ])
    def test_domain_dotted_accept(self, domain):
        """Dotted domains must be accepted (REF-01 target contract)."""
        assert validate_domain(domain) == domain

    @pytest.mark.parametrize("domain", [
        "example.c",  # 1-char TLD violates the {2,} TLD requirement (kept)
        "example..com",  # empty label between dots
        "exa mple.com",  # space is in validate_domain's dangerous-char class
    ])
    def test_domain_reject(self, domain):
        """Malformed domains raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_domain(domain)


class TestValidateUrl:
    """Characterization corpus for validate_url (no regex bug — pure lock)."""

    @pytest.mark.parametrize("url", [
        "https://example.com",
        "https://example.com/path?q=1",
        "http://192.168.1.1:8080/x",
    ])
    def test_url_accept(self, url):
        """Well-formed http(s) URLs are accepted."""
        assert validate_url(url) == url

    def test_url_space_in_netloc_accept(self):
        """Space inside the netloc is accepted by the current implementation."""
        # known limitation: space in netloc accepted today; tightening is
        # Phase 4 SSRF scope
        url = "https://exa mple.com"
        assert validate_url(url) == url

    @pytest.mark.parametrize("url", [
        "ftp://example.com",  # scheme not in the http/https allow-list
        "https://example.com/$(id)",  # dangerous characters
        "example.com",  # no scheme
    ])
    def test_url_reject(self, url):
        """Disallowed schemes, dangerous chars, and scheme-less URLs raise."""
        with pytest.raises(ValidationError):
            validate_url(url)


class TestSanitizeCommandArg:
    """Characterization corpus for sanitize_command_arg (no bug — pure lock)."""

    @pytest.mark.parametrize("arg", [
        "example.com",
        "-c 4",
        "path/to/file",
        "GET /index.html",
    ])
    def test_command_arg_accept(self, arg):
        """Benign arguments pass through unchanged."""
        assert sanitize_command_arg(arg) == arg

    @pytest.mark.parametrize("arg", [
        "foo;id",  # command chaining
        "foo|cat /etc/passwd",  # pipe to another command
        "`id`",  # backtick command substitution
        "$(id)",  # $() command substitution
        "a>b",  # output redirection
    ])
    def test_command_arg_reject(self, arg):
        """Injection patterns raise ValidationError."""
        with pytest.raises(ValidationError):
            sanitize_command_arg(arg)


class TestValidatePortRange:
    """Characterization corpus for validate_port_range (no bug — pure lock)."""

    @pytest.mark.parametrize("port_range", [
        "80",
        "80-443",
        "80,443,8080",
        "1-65535",
    ])
    def test_port_range_accept(self, port_range):
        """Valid single ports, ranges, and comma lists are accepted."""
        assert validate_port_range(port_range) == port_range

    @pytest.mark.parametrize("port_range", [
        "0-10",  # port 0 is below the valid 1-65535 bound
        "abc",  # non-numeric charset
    ])
    def test_port_range_reject(self, port_range):
        """Out-of-bound ports and invalid charsets raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_port_range(port_range)
