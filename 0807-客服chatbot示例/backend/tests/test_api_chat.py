"""API 层测试：验证 /api/health、/api/chat 的接口结构符合契约。

ChatService 通过 FastAPI 依赖覆盖注入 mock，不会真实调用 DeepSeek。
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.chat_service import ChatServiceError
from app.dependencies import get_chat_service
from app.models import ChatResponse
from app.server import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint_returns_contract_shape(app, client: TestClient) -> None:
    mock_service = MagicMock()
    mock_service.handle_chat.return_value = ChatResponse(
        session_id="abc-123",
        reply="年假需要提前在 OA 系统申请。",
        sources=["请假流程.md"],
    )
    app.dependency_overrides[get_chat_service] = lambda: mock_service

    response = client.post(
        "/api/chat", json={"session_id": "abc-123", "message": "年假怎么请"}
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"session_id", "reply", "sources"}
    assert body["session_id"] == "abc-123"
    assert isinstance(body["reply"], str)
    assert isinstance(body["sources"], list)
    assert body["sources"] == ["请假流程.md"]

    app.dependency_overrides.clear()


def test_chat_endpoint_rejects_empty_message(app, client: TestClient) -> None:
    mock_service = MagicMock()
    app.dependency_overrides[get_chat_service] = lambda: mock_service

    response = client.post("/api/chat", json={"session_id": "abc-123", "message": "  "})

    assert response.status_code == 422
    mock_service.handle_chat.assert_not_called()

    app.dependency_overrides.clear()


def test_chat_endpoint_returns_502_when_deepseek_unavailable(
    app, client: TestClient
) -> None:
    mock_service = MagicMock()
    mock_service.handle_chat.side_effect = ChatServiceError(
        "DeepSeek 未配置：请在 backend/.env 中设置 DEEPSEEK_API_KEY"
    )
    app.dependency_overrides[get_chat_service] = lambda: mock_service

    response = client.post(
        "/api/chat", json={"session_id": "abc-123", "message": "报销怎么弄"}
    )

    assert response.status_code == 502
    assert "DEEPSEEK_API_KEY" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_chat_endpoint_rejects_missing_fields(client: TestClient) -> None:
    response = client.post("/api/chat", json={"session_id": "abc-123"})
    assert response.status_code == 422
