"""DeepSeek API 客户端 — 基于 OpenAI SDK，带 JSON mode + 回退 + 重试 + 熔断。

支持同步和异步两种调用方式。
"""

from __future__ import annotations

import enum
import json
import logging
import random
import re
import time
from collections.abc import Callable
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from chinese_scraper_utils.errors import CircuitBreakerOpen

logger = logging.getLogger(__name__)

_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


def _parse_json_content(raw: str) -> dict | list:
    """解析 LLM 返回的 JSON 内容，处理 markdown 代码块包裹。"""
    content = raw.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*\n", "", content, flags=re.MULTILINE)
        content = re.sub(r"\n```\s*$", "", content)
    return json.loads(content)


def _retry_sleep(attempt: int) -> float:
    """指数退避 + jitter 的等待时间。"""
    return (2 ** attempt) * (0.5 + random.random())


class CircuitBreakerState(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """熔断器：连续失败过多时阻止 API 调用，防止雪崩。

    CLOSED → (连续 N 次失败) → OPEN → (等待 T 秒) → HALF_OPEN → (成功) → CLOSED
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._state = CircuitBreakerState.CLOSED
        self._last_failure_time = 0.0

    @property
    def state(self) -> str:
        if self._state == CircuitBreakerState.OPEN and time.monotonic() - self._last_failure_time > self.recovery_timeout:
                self._state = CircuitBreakerState.HALF_OPEN
        return self._state.value

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = CircuitBreakerState.CLOSED

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitBreakerState.OPEN


class DeepSeekClient:
    """DeepSeek API 的轻量封装 — 自动处理 JSON 输出、回退和重试。

    Usage:
        # 同步
        client = DeepSeekClient(api_key="sk-xxx")
        text = client.chat([{"role": "user", "content": "你好"}])
        data = client.chat_json([{"role": "user", "content": "输出JSON"}])

        # 异步
        text = await client.achat([{"role": "user", "content": "你好"}])
        data = await client.achat_json([{"role": "user", "content": "输出JSON"}])
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-v4-flash",
        max_retries: int = 3,
        thinking: bool = False,
    ):
        self.base_url = base_url
        self.model = model
        self.max_retries = max_retries
        self.thinking = thinking

        self._extra_body = (
            {"thinking": {"type": "enabled"}} if thinking else None
        )

        self._last_usage: dict[str, int] | None = None
        self._total_cost: float = 0.0
        self._circuit_breaker = CircuitBreaker()

        # 同步客户端
        self.client = OpenAI(api_key=api_key, base_url=base_url)

        # 异步客户端 — 懒加载，避免在不需要时导入
        self._async_client: Any = None

    @property
    def async_client(self):
        """懒加载 AsyncOpenAI 客户端。"""
        if self._async_client is None:
            from openai import AsyncOpenAI
            self._async_client = AsyncOpenAI(
                api_key=self.client.api_key,
                base_url=self.base_url,
            )
        return self._async_client

    @property
    def last_usage(self) -> dict[str, int] | None:
        """最近一次 API 调用的 token 用量统计。"""
        return self._last_usage

    @property
    def total_cost(self) -> float:
        """累计费用（USD），基于 token 用量和模型定价。"""
        return self._total_cost

    def _record_usage(self, response, model: str | None = None) -> None:
        """记录单次 API 调用的 token 用量。"""
        if hasattr(response, "usage") and response.usage:
            self._last_usage = {
                "prompt_tokens": response.usage.prompt_tokens or 0,
                "completion_tokens": response.usage.completion_tokens or 0,
                "total_tokens": response.usage.total_tokens or 0,
            }
            m = model or self.model
            if "v4-pro" in m:
                in_price = 0.28
                out_price = 1.12
            elif "flash" in m or "chat" in m:
                in_price = 0.14
                out_price = 0.28
            else:
                in_price = 0.14
                out_price = 0.28
            cost = (
                self._last_usage["prompt_tokens"] / 1_000_000 * in_price
                + self._last_usage["completion_tokens"] / 1_000_000 * out_price
            )
            self._total_cost += cost
            logger.info(
                "chat: %d prompt + %d completion = %d tokens, $%.4f (cumulative $%.4f)",
                self._last_usage["prompt_tokens"],
                self._last_usage["completion_tokens"],
                self._last_usage["total_tokens"],
                cost,
                self._total_cost,
            )

    # ═══════════════════════════════════════════════════════
    # Retry helpers — sync / async
    # ═══════════════════════════════════════════════════════

    def _sync_retry(self, create_fn: Callable[[], Any]) -> Any:
        """同步重试骨架：熔断检查 → API 调用 → 网络/HTTP 重试 → 用量记录。

        create_fn: 无参可调用对象，返回 OpenAI API 响应。
        """
        if self._circuit_breaker.state == "open":
            raise CircuitBreakerOpen()

        last_exc = None
        for attempt in range(self.max_retries):
            try:
                response = create_fn()
                self._record_usage(response)
                self._circuit_breaker.record_success()
                return response
            except (APITimeoutError, APIConnectionError) as e:
                last_exc = e
                self._circuit_breaker.record_failure()
                if attempt < self.max_retries - 1:
                    logger.debug("Network error (attempt %d): %s", attempt + 1, e)
                    time.sleep(_retry_sleep(attempt))
            except APIStatusError as e:
                if e.status_code in _RETRYABLE_STATUSES and attempt < self.max_retries - 1:
                    logger.debug("HTTP %s (attempt %d), retrying...", e.status_code, attempt + 1)
                    self._circuit_breaker.record_failure()
                    time.sleep(_retry_sleep(attempt))
                else:
                    if e.status_code not in _RETRYABLE_STATUSES:
                        self._circuit_breaker.record_failure()
                    raise
        raise last_exc or RuntimeError("max retries exceeded")

    async def _async_retry(self, create_fn: Callable[[], Any]) -> Any:
        """异步重试骨架：熔断检查 → API 调用 → 网络/HTTP 重试 → 用量记录。

        create_fn: 无参异步可调用对象，返回 OpenAI API 响应。
        """
        import asyncio

        if self._circuit_breaker.state == "open":
            raise CircuitBreakerOpen()

        last_exc = None
        for attempt in range(self.max_retries):
            try:
                response = await create_fn()
                self._record_usage(response)
                self._circuit_breaker.record_success()
                return response
            except (APITimeoutError, APIConnectionError) as e:
                last_exc = e
                self._circuit_breaker.record_failure()
                if attempt < self.max_retries - 1:
                    logger.debug("Async network error (attempt %d): %s", attempt + 1, e)
                    await asyncio.sleep(_retry_sleep(attempt))
            except APIStatusError as e:
                if e.status_code in _RETRYABLE_STATUSES and attempt < self.max_retries - 1:
                    logger.debug("Async HTTP %s (attempt %d), retrying...", e.status_code, attempt + 1)
                    self._circuit_breaker.record_failure()
                    await asyncio.sleep(_retry_sleep(attempt))
                else:
                    if e.status_code not in _RETRYABLE_STATUSES:
                        self._circuit_breaker.record_failure()
                    raise
        raise last_exc or RuntimeError("max retries exceeded")

    # ═══════════════════════════════════════════════════════
    # 同步 API
    # ═══════════════════════════════════════════════════════

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> str:
        """发送聊天请求，返回纯文本回复。内置重试 + 熔断。"""
        response = self._sync_retry(
            lambda: self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_body=self._extra_body,
            )
        )
        return (response.choices[0].message.content or "").strip()

    def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> dict | list:
        """发送聊天请求，要求 JSON 输出。解析失败时自动回退重试。内置重试 + 熔断。"""
        msgs = [dict(m) for m in messages]
        json_hint = "\n请以JSON格式输出。"
        if msgs and msgs[0]["role"] == "system":
            msgs[0] = {**msgs[0], "content": msgs[0]["content"] + json_hint}
        else:
            msgs.insert(0, {"role": "system", "content": json_hint.strip()})

        for attempt in range(self.max_retries):
            response = self._sync_retry(
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=msgs,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                    extra_body=self._extra_body,
                )
            )
            raw = (response.choices[0].message.content or "").strip()

            try:
                return _parse_json_content(raw)
            except json.JSONDecodeError:
                if attempt == self.max_retries - 1:
                    logger.debug(
                        "JSON parse failed at last attempt, retrying without JSON mode"
                    )
                    fallback = self._sync_retry(
                        lambda: self.client.chat.completions.create(
                            model=self.model,
                            messages=msgs,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            extra_body=self._extra_body,
                        )
                    )
                    raw = (fallback.choices[0].message.content or "").strip()
                    try:
                        return _parse_json_content(raw)
                    except json.JSONDecodeError as e:
                        raise ValueError(
                            f"无法解析为 JSON。原始响应前 200 字符: {raw[:200]}"
                        ) from e
                logger.debug(
                    "JSON parse failed (attempt %d), will retry with JSON mode",
                    attempt + 1,
                )
        raise RuntimeError("max retries exceeded")

    # ═══════════════════════════════════════════════════════
    # 异步 API
    # ═══════════════════════════════════════════════════════

    async def achat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> str:
        """异步版 chat()。"""
        response = await self._async_retry(
            lambda: self.async_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_body=self._extra_body,
            )
        )
        return (response.choices[0].message.content or "").strip()

    async def achat_json(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> dict | list:
        """异步版 chat_json()。"""

        msgs = [dict(m) for m in messages]
        json_hint = "\n请以JSON格式输出。"
        if msgs and msgs[0]["role"] == "system":
            msgs[0] = {**msgs[0], "content": msgs[0]["content"] + json_hint}
        else:
            msgs.insert(0, {"role": "system", "content": json_hint.strip()})

        for attempt in range(self.max_retries):
            response = await self._async_retry(
                lambda: self.async_client.chat.completions.create(
                    model=self.model,
                    messages=msgs,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                    extra_body=self._extra_body,
                )
            )
            raw = (response.choices[0].message.content or "").strip()

            try:
                return _parse_json_content(raw)
            except json.JSONDecodeError:
                if attempt == self.max_retries - 1:
                    logger.debug(
                        "Async JSON parse failed at last attempt, retrying without JSON mode"
                    )
                    fallback = await self._async_retry(
                        lambda: self.async_client.chat.completions.create(
                            model=self.model,
                            messages=msgs,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            extra_body=self._extra_body,
                        )
                    )
                    raw = (fallback.choices[0].message.content or "").strip()
                    try:
                        return _parse_json_content(raw)
                    except json.JSONDecodeError as e:
                        raise ValueError(
                            f"无法解析为 JSON。原始响应前 200 字符: {raw[:200]}"
                        ) from e
                logger.debug(
                    "Async JSON parse failed (attempt %d), will retry with JSON mode",
                    attempt + 1,
                )
        raise RuntimeError("max retries exceeded")
