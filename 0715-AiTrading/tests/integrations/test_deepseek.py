from typing import Literal

import httpx
import pytest
from pydantic import BaseModel, ConfigDict, SecretStr

from ai_trading.integrations.deepseek import (
    DeepSeekClient,
    DeepSeekClientError,
    DeepSeekErrorKind,
)


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["BUY", "SELL", "HOLD"]
    confidence: float


class RequestMessage(BaseModel):
    role: str
    content: str


class ResponseFormat(BaseModel):
    type: str


class RequestProbe(BaseModel):
    model: str
    messages: list[RequestMessage]
    response_format: ResponseFormat


SUCCESS_RESPONSE = (
    b'{"id":"chat-1","choices":[{"index":0,"message":{"role":"assistant",'
    b'"content":"{\\"action\\":\\"BUY\\",\\"confidence\\":0.82}",'
    b'"reasoning_content":"private chain of thought"},"finish_reason":"stop"}]}'
)


def test_json_completion_uses_v4_pro_and_discards_reasoning_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer deepseek-key"
        probe = RequestProbe.model_validate_json(request.content)
        assert probe.model == "deepseek-v4-pro"
        assert probe.response_format.type == "json_object"
        assert [message.role for message in probe.messages] == ["system", "user"]
        return httpx.Response(200, content=SUCCESS_RESPONSE)

    client = DeepSeekClient(
        api_key=SecretStr("deepseek-key"),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_retries=0,
    )

    result = client.complete_json(
        system_prompt="只输出 JSON",
        user_prompt="给出交易决策",
        response_model=Decision,
    )

    assert result == Decision(action="BUY", confidence=0.82)
    assert "reasoning_content" not in result.model_dump_json()
    assert "deepseek-key" not in repr(client)


def test_rate_limit_is_retried_only_within_configured_limit() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(429, content=b'{"error":"busy"}')
        return httpx.Response(200, content=SUCCESS_RESPONSE)

    client = DeepSeekClient(
        api_key=SecretStr("deepseek-key"),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_retries=1,
        retry_delay_seconds=0,
    )

    result = client.complete_json("system", "user", Decision)

    assert result.action == "BUY"
    assert call_count == 2


def test_authentication_error_is_not_retried_or_leaked() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(401, content=b'{"error":"deepseek-key is invalid"}')

    client = DeepSeekClient(
        api_key=SecretStr("deepseek-key"),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_retries=2,
    )

    with pytest.raises(DeepSeekClientError) as error:
        client.complete_json("system", "user", Decision)

    assert error.value.kind is DeepSeekErrorKind.AUTHENTICATION
    assert call_count == 1
    assert "deepseek-key" not in str(error.value)


def test_non_stop_finish_reason_is_rejected() -> None:
    response = SUCCESS_RESPONSE.replace(b'"finish_reason":"stop"', b'"finish_reason":"length"')

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=response)

    client = DeepSeekClient(
        api_key=SecretStr("deepseek-key"),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_retries=0,
    )

    with pytest.raises(DeepSeekClientError) as error:
        client.complete_json("system", "user", Decision)

    assert error.value.kind is DeepSeekErrorKind.INVALID_RESPONSE


def test_business_schema_mismatch_is_rejected_without_retry() -> None:
    response = SUCCESS_RESPONSE.replace(
        b'{\\"action\\":\\"BUY\\",\\"confidence\\":0.82}',
        b"{}",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=response)

    client = DeepSeekClient(
        api_key=SecretStr("deepseek-key"),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_retries=2,
    )

    with pytest.raises(DeepSeekClientError) as error:
        client.complete_json("system", "user", Decision)

    assert error.value.kind is DeepSeekErrorKind.SCHEMA_VALIDATION


def test_missing_api_key_fails_closed_without_http_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("缺少 API Key 时不得发起请求")

    client = DeepSeekClient(
        api_key=None,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_retries=0,
    )

    with pytest.raises(DeepSeekClientError) as error:
        client.complete_json("system", "user", Decision)

    assert error.value.kind is DeepSeekErrorKind.CONFIGURATION
