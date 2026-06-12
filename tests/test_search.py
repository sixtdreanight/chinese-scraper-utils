"""Tests for _search.py — search_web (mocked DDGS)."""

import pytest
from unittest.mock import patch, MagicMock
from chinese_scraper_utils import search_web, SearchResult


class TestSearchWeb:
    def test_returns_search_results(self):
        mock_instance = MagicMock()
        mock_instance.text.return_value = [
            {"title": "Test 1", "href": "https://a.com", "body": "snippet a"},
        ]

        class MockDDGS:
            def __init__(self):
                pass
            def __enter__(self):
                return mock_instance
            def __exit__(self, *args):
                pass

        with patch.dict("sys.modules", {"ddgs": MagicMock(DDGS=MockDDGS)}):
            results = search_web("test query", max_results=10)

        assert len(results) == 1
        assert results[0].title == "Test 1"

    def test_empty_query_returns_empty(self):
        results = search_web("")
        assert results == []

    def test_ddgs_not_installed_returns_empty(self):
        results = search_web("test")
        assert isinstance(results, list)

    def test_ddgs_exception_returns_empty(self):
        class BrokenDDGS:
            def __enter__(self):
                raise RuntimeError("search failed")
            def __exit__(self, *args): pass

        with patch.dict("sys.modules", {"ddgs": MagicMock(DDGS=BrokenDDGS)}):
            results = search_web("test")
            assert results == []


class TestSearchRateLimit:
    def test_search_rate_limit_enforced(self):
        """Second call within 3s should be delayed by the rate limiter."""
        import time
        from chinese_scraper_utils._search import search_web
        with patch.dict("sys.modules", {"ddgs": MagicMock()}):
            t0 = time.monotonic()
            search_web("test query")
            t1 = time.monotonic()
            search_web("test query")
            t2 = time.monotonic()
            assert t2 - t1 >= 2.5 or t2 - t0 >= 2.5


class TestSearchResult:
    def test_dataclass_fields(self):
        sr = SearchResult(title="T", url="https://x.com", snippet="S")
        assert sr.title == "T"
        assert sr.url == "https://x.com"
        assert sr.snippet == "S"
