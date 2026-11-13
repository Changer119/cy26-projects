"""本机访问凭据与 ASGI 鉴权；不把令牌写入日志。"""

import os
from pathlib import Path
from secrets import compare_digest, token_urlsafe

from pydantic import BaseModel, Field, SecretStr
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from ai_trading.market_mcp.models import ErrorResult


class ClientHeaders(BaseModel):
    authorization: str = Field(alias="Authorization")


class ClientServer(BaseModel):
    type: str = "http"
    url: str
    headers: ClientHeaders


class ClientConfiguration(BaseModel):
    servers: dict[str, ClientServer] = Field(alias="mcpServers")


def local_token(root: Path, port: int = 8766) -> SecretStr:
    directory = root / "data" / "market-mcp"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / "access.token"
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        token = path.read_text(encoding="utf-8").strip()
    else:
        token = token_urlsafe(32)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(token)
    if not token:
        raise ValueError("MCP 本地访问令牌为空")
    config = ClientConfiguration(
        mcpServers={
            "local-market": ClientServer(
                url=f"http://127.0.0.1:{port}/mcp",
                headers=ClientHeaders(Authorization=f"Bearer {token}"),
            )
        }
    )
    config_path = directory / "client.json"
    fd = os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(config.model_dump_json(by_alias=True, indent=2))
    return SecretStr(token)


class LocalAuthentication:
    def __init__(self, app: ASGIApp, key: SecretStr) -> None:
        self._app = app
        self._expected = f"Bearer {key.get_secret_value()}".encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"] != "/health":
            supplied = next(
                (value for name, value in scope["headers"] if name.lower() == b"authorization"), b""
            )
            if not compare_digest(supplied, self._expected):
                response = JSONResponse(
                    ErrorResult(error="需要本地 MCP 访问令牌").model_dump(), status_code=401
                )
                await response(scope, receive, send)
                return
        await self._app(scope, receive, send)
