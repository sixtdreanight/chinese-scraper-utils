"""DeepSeek API 客户端 — 基于 OpenAI SDK，带 JSON mode + 回退 + 重试。

支持同步和异步两种调用方式。
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
from typing import Any

from openai import APIStatusError, APITimeoutError, APIConnectionError, OpenAI

logger = logging.getLogger(__name__)

_RETRYABLE_STATUSES = frozenset({429, 503})


def _parse_json_content(raw: str) -> dict | list:
    """解析 LLM 返回的 JSON 内容，处理 markdown 代码块包裹。"""
    content = raw.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*\n", "", content)
        content = re.sub(r"\n```\s*$", "", content)
    return json.loads(content)


def _retry_sleep(attempt: int) -> float:
    """指数退避 + jitter 的等待时间。"""
    return (2 ** attempt) * (0.5 + random.random())


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
        model: str = "deepseek-chat",
        max_retries: int = 3,
    ):
        self.base_url = base_url
        self.model = model
        self.max_retries = max_retries

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

    # ═══════════════════════════════════════════════════════
    # 同步 API
    # ═══════════════════════════════════════════════════════

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> str:
        """发送聊天请求，返回纯文本回复。内置 429/503 重试。"""
        last_exc = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return (response.choices[0].message.content or "").strip()
            except (APITimeoutError, APIConnectionError) as e:
                last_exc = e
                if attempt < self.max_retries - 1:
                    logger.debug("Network error (attempt %d): %s", attempt + 1, e)
                    time.sleep(_retry_sleep(attempt))
            except APIStatusError as e:
                if e.status_code in _RETRYABLE_STATUSES and attempt < self.max_retries - 1:
                    logger.debug("HTTP %s (attempt %d), retrying...", e.status_code, attempt + 1)
                    time.sleep(_retry_sleep(attempt))
                else:
                    raise
        raise last_exc or RuntimeError("max retries exceeded")

    def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> dict | list:
        """发送聊天请求，要求 JSON 输出。解析失败时自动回退重试。内置 429/503 重试。"""
        msgs = [dict(m) for m in messages]
        json_hint = "\n请以JSON格式输出。"
        if msgs and msgs[0]["role"] == "system":
            msgs[0] = {**msgs[0], "content": msgs[0]["content"] + json_hint}
        else:
            msgs.insert(0, {"role": "system", "content": json_hint.strip()})

        last_exc = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=msgs,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )
                raw = (response.choices[0].message.content or "").strip()

                try:
                    return _parse_json_content(raw)
                except json.JSONDecodeError:
                    logger.debug(
                        "JSON parse failed (attempt %d), retrying without JSON mode",
                        attempt + 1,
                    )
                    # 回退：不加 JSON mode 重试
                    fallback = self.client.chat.completions.create(
                        model=self.model,
                        messages=msgs,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    raw = (fallback.choices[0].message.content or "").strip()
                    try:
                        return _parse_json_content(raw)
                    except json.JSONDecodeError as e:
                        raise ValueError(
                            f"无法解析为 JSON。原始响应前 200 字符: {raw[:200]}"
                        ) from e

            except (APITimeoutError, APIConnectionError) as e:
                last_exc = e
                if attempt < self.max_retries - 1:
                    logger.debug("Network error (attempt %d): %s", attempt + 1, e)
                    time.sleep(_retry_sleep(attempt))
            except APIStatusError as e:
                if e.status_code in _RETRYABLE_STATUSES and attempt < self.max_retries - 1:
                    logger.debug("HTTP %s (attempt %d), retrying...", e.status_code, attempt + 1)
                    time.sleep(_retry_sleep(attempt))
                else:
                    raise

        raise last_exc or RuntimeError("max retries exceeded")

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
        import asyncio

        last_exc = None
        for attempt in range(self.max_retries):
            try:
                response = await self.async_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return (response.choices[0].message.content or "").strip()
            except (APITimeoutError, APIConnectionError) as e:
                last_exc = e
                if attempt < self.max_retries - 1:
                    logger.debug("Async network error (attempt %d): %s", attempt + 1, e)
                    await asyncio.sleep(_retry_sleep(attempt))
            except APIStatusError as e:
                if e.status_code in _RETRYABLE_STATUSES and attempt < self.max_retries - 1:
                    logger.debug("Async HTTP %s (attempt %d), retrying...", e.status_code, attempt + 1)
                    await asyncio.sleep(_retry_sleep(attempt))
                else:
                    raise
        raise last_exc or RuntimeError("max retries exceeded")

    async def achat_json(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> dict | list:
        """异步版 chat_json()。"""
        import asyncio

        msgs = [dict(m) for m in messages]
        json_hint = "\n请以JSON格式输出。"
        if msgs and msgs[0]["role"] == "system":
            msgs[0] = {**msgs[0], "content": msgs[0]["content"] + json_hint}
        else:
            msgs.insert(0, {"role": "system", "content": json_hint.strip()})

        last_exc = None
        for attempt in range(self.max_retries):
            try:
                response = await self.async_client.chat.completions.create(
                    model=self.model,
                    messages=msgs,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )
                raw = (response.choices[0].message.content or "").strip()

                try:
                    return _parse_json_content(raw)
                except json.JSONDecodeError:
                    logger.debug(
                        "Async JSON parse failed (attempt %d), retrying without JSON mode",
                        attempt + 1,
                    )
                    fallback = await self.async_client.chat.completions.create(
                        model=self.model,
                        messages=msgs,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    raw = (fallback.choices[0].message.content or "").strip()
                    try:
                        return _parse_json_content(raw)
                    except json.JSONDecodeError as e:
                        raise ValueError(
                            f"无法解析为 JSON。原始响应前 200 字符: {raw[:200]}"
                        ) from e

            except (APITimeoutError, APIConnectionError) as e:
                last_exc = e
                if attempt < self.max_retries - 1:
                    logger.debug("Async network error (attempt %d): %s", attempt + 1, e)
                    await asyncio.sleep(_retry_sleep(attempt))
            except APIStatusError as e:
                if e.status_code in _RETRYABLE_STATUSES and attempt < self.max_retries - 1:
                    logger.debug("Async HTTP %s (attempt %d), retrying...", e.status_code, attempt + 1)
                    await asyncio.sleep(_retry_sleep(attempt))
                else:
                    raise

        raise last_exc or RuntimeError("max retries exceeded")
