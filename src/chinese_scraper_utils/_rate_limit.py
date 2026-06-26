"""异步速率限制器 — 请求间最小间隔 + 指数退避重试。"""

import asyncio
import random
import time

import httpx

from chinese_scraper_utils.errors import NetworkError, RateLimitError

# 可重试的 HTTP 状态码（与 _ai.py 中的 DeepSeekClient 保持一致）
_RETRYABLE_STATUSES = (429, 500, 502, 503, 504)


class RateLimiter:
    """异步速率限制器，保证两次请求之间至少间隔 min_interval 秒。"""

    def __init__(self, min_interval: float = 2.0):
        self.min_interval = min_interval
        self._last_request = 0.0
        self._lock = asyncio.Lock()

    async def wait(self):
        """等待直到可以发起下一次请求。使用锁防止 TOCTOU 竞态。"""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
            self._last_request = time.monotonic()

    async def fetch_with_retry(self, fetch_fn, max_retries: int = 3):
        """带指数退避 + jitter 的请求包装器。

        fetch_fn: 无参异步函数，返回响应对象。
        """
        last_exc = None
        for attempt in range(max_retries):
            try:
                await self.wait()
                resp = await fetch_fn()
                if hasattr(resp, "status_code") and resp.status_code in _RETRYABLE_STATUSES:
                    if attempt < max_retries - 1:
                        wait_s = (2 ** attempt) * (0.5 + random.random())  # nosec B311
                        await asyncio.sleep(wait_s)
                        continue
                    raise RateLimitError(
                        f"HTTP {resp.status_code} after {max_retries} retries"
                    )
                return resp
            except Exception as e:
                last_exc = e
                if attempt < max_retries - 1:
                    wait_s = (2 ** attempt) * (0.5 + random.random())  # nosec B311
                    await asyncio.sleep(wait_s)
        if last_exc:
            if isinstance(last_exc, httpx.HTTPStatusError):
                if last_exc.response.status_code in _RETRYABLE_STATUSES:
                    raise RateLimitError(str(last_exc), retry_after=None) from last_exc
                raise NetworkError(str(last_exc), url=str(last_exc.request.url) if last_exc.request else "") from last_exc
            # Wrap all other httpx errors (ConnectError, TimeoutException, etc.) as NetworkError
            if isinstance(last_exc, httpx.HTTPError):
                raise NetworkError(str(last_exc), url="") from last_exc
            raise last_exc
        raise RuntimeError("max retries exceeded")

    def limit(self, func):
        """装饰器：为异步函数添加速率限制。

        Usage:
            limiter = RateLimiter(min_interval=1.0)

            @limiter.limit
            async def fetch(url: str) -> dict:
                ...
        """
        import functools

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            await self.wait()
            return await func(*args, **kwargs)

        return wrapper
