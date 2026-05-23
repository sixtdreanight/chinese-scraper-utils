"""DeepSeek API 客户端 — 基于 OpenAI SDK，带 JSON mode + 回退。"""

import json
import re
from openai import OpenAI


class DeepSeekClient:
    """DeepSeek API 的轻量封装，自动处理 JSON 输出和回退。"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
    ):
        self.base_url = base_url
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> str:
        """发送聊天请求，返回纯文本回复。"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()

    def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> dict:
        """发送聊天请求，要求 JSON 输出。解析失败时自动回退重试。"""
        msgs = [dict(m) for m in messages]
        json_hint = "\n请以JSON格式输出。"
        if msgs and msgs[0]["role"] == "system":
            msgs[0] = {**msgs[0], "content": msgs[0]["content"] + json_hint}
        else:
            msgs.insert(0, {"role": "system", "content": json_hint.strip()})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=msgs,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*\n", "", raw)
            raw = re.sub(r"\n```\s*$", "", raw)

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            fallback = self.client.chat.completions.create(
                model=self.model,
                messages=msgs,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            raw = fallback.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*\n", "", raw)
                raw = re.sub(r"\n```\s*$", "", raw)
            try:
                return json.loads(raw)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"两次尝试均无法解析为 JSON。原始响应前 200 字符: {raw[:200]}"
                ) from e
