"""异步速率限制器 — 请求间最小间隔 + 指数退避重试。"""

import time
import asyncio


class RateLimiter:
    """异步速率限制器，保证两次请求之间至少间隔 min_interval 秒。"""

    def __init__(self, min_interval: float = 2.0):
        self.min_interval = min_interval
        self._last_request = 0.0

    async def wait(self):
        """等待直到可以发起下一次请求。"""
        now = time.monotonic()
        elapsed = now - self._last_request
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self._last_request = time.monotonic()

    async def fetch_with_retry(self, fetch_fn, max_retries: int = 3):
        """带指数退避的请求包装器。

        fetch_fn: 无参异步函数，返回响应对象。
        """
        last_exc = None
        for attempt in range(max_retries):
            try:
                await self.wait()
                resp = await fetch_fn()
                if hasattr(resp, "status_code") and resp.status_code in (429, 503):
                    wait_s = 2 ** attempt
                    await asyncio.sleep(wait_s)
                    continue
                return resp
            except Exception as e:
                last_exc = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        raise last_exc or RuntimeError("max retries exceeded")
