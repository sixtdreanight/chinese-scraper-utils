"""Tests for errors.py — all exception constructors and inheritance."""

import pytest
from chinese_scraper_utils.errors import (
    ScraperError,
    RateLimitError,
    ExtractionError,
    ValidationError,
    NetworkError,
    CircuitBreakerOpen,
)


class TestScraperError:
    def test_is_base_exception(self):
        assert issubclass(ScraperError, Exception)

    def test_default_message(self):
        err = ScraperError()
        assert str(err) == ""


class TestRateLimitError:
    def test_default_message(self):
        err = RateLimitError()
        assert str(err) == "Rate limit exceeded"
        assert err.retry_after is None

    def test_custom_message(self):
        err = RateLimitError(message="custom")
        assert str(err) == "custom"

    def test_with_retry_after(self):
        err = RateLimitError(retry_after=30.0)
        assert err.retry_after == 30.0

    def test_inheritance(self):
        assert issubclass(RateLimitError, ScraperError)


class TestExtractionError:
    def test_default(self):
        err = ExtractionError()
        assert str(err) == "Extraction failed"
        assert err.raw_response is None

    def test_with_raw_response(self):
        err = ExtractionError(raw_response="not json")
        assert err.raw_response == "not json"

    def test_inheritance(self):
        assert issubclass(ExtractionError, ScraperError)


class TestValidationError:
    def test_default(self):
        err = ValidationError()
        assert str(err) == "Validation failed"
        assert err.field == ""
        assert err.value == ""

    def test_with_field_value(self):
        err = ValidationError(field="date", value="invalid")
        assert err.field == "date"
        assert err.value == "invalid"

    def test_inheritance(self):
        assert issubclass(ValidationError, ScraperError)


class TestNetworkError:
    def test_default(self):
        err = NetworkError()
        assert str(err) == "Network error"
        assert err.url == ""

    def test_with_url(self):
        err = NetworkError(url="https://example.com")
        assert err.url == "https://example.com"

    def test_inheritance(self):
        assert issubclass(NetworkError, ScraperError)


class TestCircuitBreakerOpen:
    def test_default(self):
        err = CircuitBreakerOpen()
        assert "Circuit breaker" in str(err)
        assert err.retry_after is None

    def test_with_retry_after(self):
        err = CircuitBreakerOpen(retry_after=120.0)
        assert err.retry_after == 120.0

    def test_inheritance(self):
        assert issubclass(CircuitBreakerOpen, ScraperError)
