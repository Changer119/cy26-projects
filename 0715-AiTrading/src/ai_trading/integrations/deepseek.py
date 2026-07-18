"""DeepSeek Chat Completions 的受控 JSON 客户端。"""

from __future__ import annotations

import time
from collections.abc import Callable
from enum import StrEnum
from typing import Literal, TypeVar

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class DeepSeekErrorKind(StrEnum):
    CONFIGURATION = "CONFIGURATION"
    AUTHENTICATION = "AUTHENTICATION"
    RATE_LIMIT = "RATE_LIMIT"
    TRANSIENT = "TRANSIENT"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    SCHEMA_VALIDATION = "SCHEMA_VALIDATION"


class DeepSeekClientError(RuntimeError):
    """只保存已脱敏的错误分类和说明。"""

    def __init__(self, kind: DeepSeekErrorKind, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable


class _RequestMessage(BaseModel):
    role: Literal["system", "user"]
    content: str


class _ResponseFormat(BaseModel):
    type: Literal["json_object"] = "json_object"


class _CompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: Literal["deepseek-v4-pro"] = "deepseek-v4-pro"
    messages: tuple[_RequestMessage, _RequestMessage]
    response_format: _ResponseFormat = Field(default_factory=_ResponseFormat)


class _ResponseMessage(BaseModel):
    """刻意不声明 reasoning_content, 解析时直接丢弃。"""

    model_config = ConfigDict(extra="ignore")

    role: str
    content: str | None = None


class _CompletionChoice(BaseModel):
    model_config = ConfigDict(extra="ignore")

    index: int
    message: _ResponseMessage
    finish_reason: str | None


class _CompletionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    choices: list[_CompletionChoice]


class DeepSeekClient:
    """固定 v4-pro, 并仅返回调用方声明的 Pydantic 模型。"""

    def __init__(
        self,
        api_key: SecretStr | None,
        http_client: httpx.Client,
        max_retries: int = 2,
        retry_delay_seconds: float = 0.5,
        sleeper: Callable[[float], None] = time.sleep,
        base_url: str = "https://api.deepseek.com",
    ) -> None:
        self._api_key = api_key
        self._http_client = http_client
        self._max_retries = max_retries
        self._retry_delay_seconds = retry_delay_seconds
        self._sleeper = sleeper
        self._base_url = base_url.rstrip("/")

    def __repr__(self) -> str:
        return f"{type(self).__name__}(model='deepseek-v4-pro', api_key=SecretStr('**********'))"

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[ResponseT],
    ) -> ResponseT:
        api_key = self._read_api_key()
        payload = _CompletionRequest(
            messages=(
                _RequestMessage(role="system", content=system_prompt),
                _RequestMessage(role="user", content=user_prompt),
            )
        ).model_dump_json()

        for attempt in range(self._max_retries + 1):
            try:
                response = self._http_client.post(
                    f"{self._base_url}/chat/completions",
                    content=payload,
                    headers=(
                        ("Authorization", f"Bearer {api_key}"),
                        ("Content-Type", "application/json"),
                    ),
                )
            except httpx.HTTPError as exc:
                error = DeepSeekClientError(
                    DeepSeekErrorKind.TRANSIENT,
                    "DeepSeek 网络请求失败",
                    retryable=True,
                )
                if self._retry(error, attempt):
                    continue
                raise error from exc

            status_error = self._classify_status(response.status_code)
            if status_error is not None:
                if self._retry(status_error, attempt):
                    continue
                raise status_error
            return self._parse_response(response.content, response_model)

        raise DeepSeekClientError(DeepSeekErrorKind.TRANSIENT, "DeepSeek 重试耗尽")

    def _read_api_key(self) -> str:
        if self._api_key is None or not self._api_key.get_secret_value().strip():
            raise DeepSeekClientError(
                DeepSeekErrorKind.CONFIGURATION,
                "未配置 DeepSeek API Key, AI 决策已关闭",
            )
        return self._api_key.get_secret_value().strip()

    def _retry(self, error: DeepSeekClientError, attempt: int) -> bool:
        if not error.retryable or attempt >= self._max_retries:
            return False
        if self._retry_delay_seconds > 0:
            self._sleeper(self._retry_delay_seconds)
        return True

    @staticmethod
    def _classify_status(status_code: int) -> DeepSeekClientError | None:
        if status_code in (401, 403):
            return DeepSeekClientError(
                DeepSeekErrorKind.AUTHENTICATION,
                "DeepSeek 鉴权失败",
            )
        if status_code == 429:
            return DeepSeekClientError(
                DeepSeekErrorKind.RATE_LIMIT,
                "DeepSeek 请求受限",
                retryable=True,
            )
        if status_code >= 500:
            return DeepSeekClientError(
                DeepSeekErrorKind.TRANSIENT,
                f"DeepSeek 服务暂时不可用 (HTTP {status_code})",
                retryable=True,
            )
        if status_code >= 400:
            return DeepSeekClientError(
                DeepSeekErrorKind.INVALID_RESPONSE,
                f"DeepSeek 拒绝了请求 (HTTP {status_code})",
            )
        return None

    @staticmethod
    def _parse_response(content: bytes, response_model: type[ResponseT]) -> ResponseT:
        try:
            completion = _CompletionResponse.model_validate_json(content)
        except ValidationError as exc:
            raise DeepSeekClientError(
                DeepSeekErrorKind.INVALID_RESPONSE,
                "DeepSeek 响应结构无效",
            ) from exc
        if not completion.choices:
            raise DeepSeekClientError(
                DeepSeekErrorKind.INVALID_RESPONSE,
                "DeepSeek 响应没有候选结果",
            )
        choice = completion.choices[0]
        if choice.finish_reason != "stop" or choice.message.content is None:
            raise DeepSeekClientError(
                DeepSeekErrorKind.INVALID_RESPONSE,
                "DeepSeek 未完整生成 JSON 结果",
            )
        try:
            return response_model.model_validate_json(choice.message.content)
        except ValidationError as exc:
            raise DeepSeekClientError(
                DeepSeekErrorKind.SCHEMA_VALIDATION,
                "DeepSeek JSON 不符合业务 schema",
            ) from exc
