"""Tests for _rate_limit.py — RateLimiter."""

import time
import asyncio
import pytest
from chinese_scraper_utils import RateLimiter


class TestRateLimiterWait:
    def test_wait_enforces_interval(self):
        limiter = RateLimiter(min_interval=0.1)
        t0 = time.monotonic()
        asyncio.run(limiter.wait())
        t1 = time.monotonic()
        assert t1 - t0 < 0.05  # first call should be instant

        asyncio.run(limiter.wait())
        t2 = time.monotonic()
        assert t2 - t1 >= 0.09  # second call should wait ~0.1s

    def test_wait_concurrent_safety(self):
        """TOCTOU regression: two concurrent waits should each get their own slot."""
        limiter = RateLimiter(min_interval=0.05)

        async def concurrent_waits():
            t0 = time.monotonic()
            await asyncio.gather(
                limiter.wait(),
                limiter.wait(),
            )
            elapsed = time.monotonic() - t0
            # 两个等待串行执行应该至少 0.05s 间隔
            assert elapsed >= 0.04

        asyncio.run(concurrent_waits())

    def test_default_interval(self):
        limiter = RateLimiter()
        assert limiter.min_interval == 2.0


class TestFetchWithRetry:
    def test_successful_fetch(self):
        limiter = RateLimiter(min_interval=0.01)

        async def fetch():
            class FakeResponse:
                status_code = 200
            return FakeResponse()

        resp = asyncio.run(limiter.fetch_with_retry(fetch))
        assert resp.status_code == 200

    def test_retry_on_429(self):
        limiter = RateLimiter(min_interval=0.01)
        call_count = [0]

        async def fetch():
            call_count[0] += 1
            class FakeResponse:
                pass
            resp = FakeResponse()
            if call_count[0] < 2:
                resp.status_code = 429
            else:
                resp.status_code = 200
            return resp

        resp = asyncio.run(limiter.fetch_with_retry(fetch, max_retries=3))
        assert resp.status_code == 200
        assert call_count[0] == 2

    def test_retry_on_exception(self):
        limiter = RateLimiter(min_interval=0.01)
        call_count = [0]

        async def fetch():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ConnectionError("fail")
            class FakeResponse:
                status_code = 200
            return FakeResponse()

        resp = asyncio.run(limiter.fetch_with_retry(fetch, max_retries=3))
        assert resp.status_code == 200

    def test_max_retries_exceeded(self):
        limiter = RateLimiter(min_interval=0.01)

        async def fetch():
            raise ConnectionError("always fails")

        with pytest.raises(ConnectionError):
            asyncio.run(limiter.fetch_with_retry(fetch, max_retries=2))


class TestRateLimitDecorator:
    def test_decorator_works(self):
        limiter = RateLimiter(min_interval=0.01)

        @limiter.limit
        async def fetch(x):
            return x * 2

        result = asyncio.run(fetch(5))
        assert result == 10

    def test_decorator_preserves_name(self):
        limiter = RateLimiter(min_interval=0.01)

        @limiter.limit
        async def my_func():
            pass

        assert my_func.__name__ == "my_func"


class TestFetchWithRetryErrors:
    def test_raises_rate_limit_error_on_429(self):
        from chinese_scraper_utils.errors import RateLimitError
        from unittest.mock import patch
        limiter = RateLimiter(min_interval=0.01)

        async def fetch():
            class FakeResponse:
                status_code = 429
            return FakeResponse()

        with patch("chinese_scraper_utils._rate_limit.asyncio.sleep", return_value=None):
            try:
                asyncio.run(limiter.fetch_with_retry(fetch, max_retries=2))
            except RateLimitError:
                return
            # Should have raised RateLimitError
            assert False, "Expected RateLimitError"

    def test_raises_network_error_on_http_error(self):
        from chinese_scraper_utils.errors import NetworkError
        import httpx
        from unittest.mock import patch
        limiter = RateLimiter(min_interval=0.01)

        async def fetch():
            raise httpx.ConnectError("connection refused")

        with patch("chinese_scraper_utils._rate_limit.asyncio.sleep", return_value=None):
            try:
                asyncio.run(limiter.fetch_with_retry(fetch, max_retries=2))
            except NetworkError:
                return
            assert False, "Expected NetworkError"
