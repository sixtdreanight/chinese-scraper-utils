"""Tests for _ai.py — DeepSeekClient (with mocks)."""

import json
import pytest
from unittest.mock import patch, MagicMock
from chinese_scraper_utils import DeepSeekClient
from openai import APIStatusError


@pytest.fixture
def client():
    return DeepSeekClient(api_key="sk-test", model="deepseek-v4-flash", max_retries=2)


class TestDeepSeekClientInit:
    def test_default_values(self, client):
        assert client.model == "deepseek-v4-flash"
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

    def test_chat_json_retries_on_parse_failure(self, client):
        """Last attempt: fallback without JSON mode after parse failure."""
        json_fail = MagicMock()
        json_fail.content = "not valid json {"

        json_ok = MagicMock()
        json_ok.content = '{"ok": true}'

        with patch.object(client.client.chat.completions, "create") as mock_create:
            mock_create.side_effect = [
                MagicMock(choices=[MagicMock(message=json_fail)]),
                MagicMock(choices=[MagicMock(message=json_ok)]),
            ]
            result = client.chat_json([{"role": "user", "content": "test"}])
            assert result == {"ok": True}
            assert mock_create.call_count >= 2


class TestTotalCost:
    def test_total_cost_starts_at_zero(self, client):
        assert client.total_cost == 0.0

    def test_total_cost_does_not_raise_before_api_call(self, client):
        """Regression: accessing total_cost before any call should not raise."""
        assert client.total_cost == 0.0


class TestCircuitBreaker:
    @pytest.fixture
    def cb(self):
        from chinese_scraper_utils._ai import CircuitBreaker
        return CircuitBreaker(failure_threshold=2, recovery_timeout=10.0)

    def test_initial_state(self, cb):
        assert cb.state == "closed"

    def test_records_failures(self, cb):
        cb.record_failure()
        assert cb.state == "closed"
        cb.record_failure()
        assert cb.state == "open"

    def test_records_success_resets(self, cb):
        cb.record_failure()
        cb.record_success()
        assert cb.state == "closed"

    def test_recovery_timeout(self, cb):
        import time
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        # Simulate timeout by modifying internals
        cb._last_failure_time = time.monotonic() - 20.0
        assert cb.state == "half_open"


class TestAsyncChat:
    @pytest.mark.asyncio
    async def test_achat_returns_text(self, client):
        import asyncio
        mock_msg = MagicMock()
        mock_msg.content = "Async response"

        class AsyncChoices:
            def __init__(self, msg):
                self.choices = [msg]

        with patch.object(client, "_async_retry") as mock_retry:
            fake_resp = MagicMock()
            fake_resp.choices = [MagicMock(message=mock_msg)]
            mock_retry.return_value = fake_resp
            result = await client.achat([{"role": "user", "content": "hi"}])
            assert result == "Async response"

    @pytest.mark.asyncio
    async def test_achat_json_returns_dict(self, client):
        import asyncio
        mock_msg = MagicMock()
        mock_msg.content = '{"result": "async"}'

        with patch.object(client, "_async_retry") as mock_retry:
            fake_resp = MagicMock()
            fake_resp.choices = [MagicMock(message=mock_msg)]
            mock_retry.return_value = fake_resp
            result = await client.achat_json([{"role": "user", "content": "json"}])
            assert result == {"result": "async"}


class TestCircuitBreakerIntegration:
    def test_chat_blocked_when_breaker_open(self, client):
        from chinese_scraper_utils._ai import CircuitBreaker
        from chinese_scraper_utils.errors import CircuitBreakerOpen
        client._circuit_breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=999)
        client._circuit_breaker.record_failure()

        with pytest.raises(CircuitBreakerOpen):
            client.chat([{"role": "user", "content": "test"}])


class TestAsyncClientLazyInit:
    def test_async_client_created_on_demand(self, client):
        assert client._async_client is None
        ac = client.async_client
        assert ac is not None
        assert client._async_client is not None
