"""Tests for _ua.py — random_ua, UA_POOL."""

import pytest
from chinese_scraper_utils import random_ua, UA_POOL


class TestUAPool:
    def test_min_size(self):
        assert len(UA_POOL) >= 20, f"UA_POOL should have at least 20 entries, got {len(UA_POOL)}"

    def test_no_duplicates(self):
        """No identical entries."""
        seen = set()
        for ua in UA_POOL:
            normalized = ua.strip()
            assert normalized not in seen, f"Duplicate UA: {ua[:80]}..."
            seen.add(normalized)

    def test_valid_format(self):
        """All UAs should start with 'Mozilla/'."""
        for ua in UA_POOL:
            assert ua.startswith("Mozilla/"), f"Invalid UA: {ua[:60]}..."

    def test_variety(self):
        """Should contain entries from different browsers/platforms."""
        pool_text = " ".join(UA_POOL)
        assert "Chrome" in pool_text
        assert "Firefox" in pool_text
        assert "Safari" in pool_text


class TestRandomUA:
    def test_returns_string(self):
        assert isinstance(random_ua(), str)

    def test_returns_from_pool(self):
        for _ in range(50):
            assert random_ua() in UA_POOL

    def test_randomness(self):
        """After 100 calls, should have used multiple different UAs."""
        results = {random_ua() for _ in range(100)}
        assert len(results) >= 5, "Should use at least 5 different UAs"
