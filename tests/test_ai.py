"""Tests for _ai.py — DeepSeekClient (with mocks)."""

import json
import pytest
from unittest.mock import patch, MagicMock
from chinese_scraper_utils import DeepSeekClient
from openai import APIStatusError


@pytest.fixture
def client():
    return DeepSeekClient(api_key="sk-test", model="deepseek-chat", max_retries=2)


class TestDeepSeekClientInit:
    def test_default_values(self, client):
        assert client.model == "deepseek-chat"
        assert client.base_url == "https://api.deepseek.com"
        assert client.max_retries == 2

    def test_custom_retries(self):
        client = DeepSeekClient(api_key="sk-test", max_retries=5)
        assert client.max_retries == 5


class TestChat:
    def test_chat_returns_text(self, client):
        mock_msg = MagicMock()
        mock_msg.content = "你好，有什么可以帮助你的？"

        with patch.object(client.client.chat.completions, "create") as mock_create:
            mock_create.return_value = MagicMock(
                choices=[MagicMock(message=mock_msg)]
            )
            result = client.chat([{"role": "user", "content": "你好"}])
            assert result == "你好，有什么可以帮助你的？"

    def test_chat_retries_on_429(self, client):
        mock_msg = MagicMock()
        mock_msg.content = "OK"

        with patch.object(client.client.chat.completions, "create") as mock_create:
            error_429 = APIStatusError("rate limited", response=MagicMock(status_code=429), body=None)
            mock_create.side_effect = [
                error_429,
                MagicMock(choices=[MagicMock(message=mock_msg)]),
            ]
            result = client.chat([{"role": "user", "content": "test"}])
            assert result == "OK"
            assert mock_create.call_count == 2

    def test_chat_raises_on_non_retryable(self, client):
        with patch.object(client.client.chat.completions, "create") as mock_create:
            error_400 = APIStatusError("bad request", response=MagicMock(status_code=400), body=None)
            mock_create.side_effect = error_400

            with pytest.raises(APIStatusError):
                client.chat([{"role": "user", "content": "test"}])


class TestChatJSON:
    def test_chat_json_returns_dict(self, client):
        mock_msg = MagicMock()
        mock_msg.content = '{"key": "value"}'

        with patch.object(client.client.chat.completions, "create") as mock_create:
            mock_create.return_value = MagicMock(
                choices=[MagicMock(message=mock_msg)]
            )
            result = client.chat_json([{"role": "user", "content": "输出JSON"}])
            assert result == {"key": "value"}

    def test_chat_json_strips_markdown_fence(self, client):
        mock_msg = MagicMock()
        mock_msg.content = '```json\n{"key": "value"}\n```'

        with patch.object(client.client.chat.completions, "create") as mock_create:
            mock_create.return_value = MagicMock(
                choices=[MagicMock(message=mock_msg)]
            )
            result = client.chat_json([{"role": "user", "content": "输出JSON"}])
            assert result == {"key": "value"}

    def test_chat_json_adds_json_hint(self, client):
        mock_msg = MagicMock()
        mock_msg.content = '{"ok": true}'

        with patch.object(client.client.chat.completions, "create") as mock_create:
            mock_create.return_value = MagicMock(
                choices=[MagicMock(message=mock_msg)]
            )
            client.chat_json([{"role": "user", "content": "test"}])

            # Verify the call included system message with JSON hint
            call_args = mock_create.call_args_list[0][1]
            messages = call_args["messages"]
            assert any("JSON" in m.get("content", "") for m in messages if m["role"] == "system")
            assert call_args.get("response_format") == {"type": "json_object"}
