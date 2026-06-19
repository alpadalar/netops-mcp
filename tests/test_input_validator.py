"""
Tests for hostname/domain validators in validators/input_validator.py.

Guards the escaped-dot fix: the label-separator must be a literal dot. The
previous patterns used ``\\.`` (a backslash followed by "any char") in a raw
string and so rejected every multi-label name while still notionally matching
non-dot separators.
"""

import pytest

from netops_mcp.validators.input_validator import (
    ValidationError,
    validate_domain,
    validate_hostname,
)


class TestValidateHostname:
    @pytest.mark.parametrize(
        "value",
        [
            "google.com",
            "a.b.com",
            "example.co.uk",
            "deep.sub.domain.example.com",
            "localhost",
            "192.168.1.1",
            "127.0.0.1",
            "10.0.0.1",
        ],
    )
    def test_accepts_valid(self, value):
        assert validate_hostname(value) == value

    def test_multilabel_names_accepted_regression(self):
        # Before the fix the broken `\\.` pattern rejected these outright.
        assert validate_hostname("a.b.com") == "a.b.com"
        assert validate_hostname("deep.sub.domain.com") == "deep.sub.domain.com"

    @pytest.mark.parametrize(
        "value",
        [
            "a;b.com",
            "a&b.com",
            "a|b.com",
            "a`b.com",
            "a$b.com",
            "a(b).com",
            "host with spaces",
            "-leading.com",
            "trailing-.com",
            "a..b.com",
            "example.com.",
            "bad_underscore.com",
        ],
    )
    def test_rejects_invalid(self, value):
        with pytest.raises(ValidationError):
            validate_hostname(value)

    @pytest.mark.parametrize("value", ["", None])
    def test_rejects_empty(self, value):
        with pytest.raises(ValidationError):
            validate_hostname(value)

    def test_rejects_crlf_injection(self):
        with pytest.raises(ValidationError):
            validate_hostname("good.com\nrm -rf /")

    def test_loopback_rejected_when_disallowed(self):
        with pytest.raises(ValidationError):
            validate_hostname("127.0.0.1", allow_localhost=False)


class TestValidateDomain:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("google.com", "google.com"),
            ("a.b.com", "a.b.com"),
            ("example.co.uk", "example.co.uk"),
            ("sub.domain.com", "sub.domain.com"),
            ("test-domain.org", "test-domain.org"),
            ("localhost", "localhost"),  # single-label allowed for internal use
            ("EXAMPLE.COM", "example.com"),  # normalized to lowercase
        ],
    )
    def test_accepts_valid(self, value, expected):
        assert validate_domain(value) == expected

    def test_multilabel_names_accepted_regression(self):
        assert validate_domain("a.b.com") == "a.b.com"

    @pytest.mark.parametrize(
        "value",
        [
            "a;b.com",
            "domain with spaces",
            "domain@invalid",
            "invalid..domain",
            "-lead.com",
            "trail-.com",
        ],
    )
    def test_rejects_invalid(self, value):
        with pytest.raises(ValidationError):
            validate_domain(value)

    @pytest.mark.parametrize("value", ["", None])
    def test_rejects_empty(self, value):
        with pytest.raises(ValidationError):
            validate_domain(value)
