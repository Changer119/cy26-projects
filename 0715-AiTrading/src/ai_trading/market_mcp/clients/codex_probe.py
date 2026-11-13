"""通过 Codex app-server 只读列举 MCP 工具，不创建会话或调用模型。"""

import selectors
import subprocess
from time import monotonic
from typing import Literal

from pydantic import BaseModel, Field, JsonValue


class ClientInfo(BaseModel):
    name: str = "market-mcp-check"
    version: str = "1.0.0"


class InitializeParams(BaseModel):
    client_info: ClientInfo = Field(default_factory=ClientInfo, alias="clientInfo")


class ListParams(BaseModel):
    limit: int = 100


class Request(BaseModel):
    id: int
    method: str
    params: InitializeParams | ListParams


class Notification(BaseModel):
    method: Literal["initialized"] = "initialized"


class Envelope(BaseModel):
    id: int | None = None
    result: JsonValue = None
    error: JsonValue = None


class ServerStatus(BaseModel):
    name: str
    tools: dict[str, JsonValue] = Field(default_factory=dict)


class StatusResult(BaseModel):
    data: list[ServerStatus]


def probe_codex() -> tuple[str, ...]:
    with subprocess.Popen(
        ["codex", "app-server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    ) as process:
        assert process.stdin is not None and process.stdout is not None
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)

        def exchange(request: Request) -> Envelope:
            assert process.stdin is not None and process.stdout is not None
            process.stdin.write(request.model_dump_json(by_alias=True) + "\n")
            process.stdin.flush()
            deadline = monotonic() + 40
            while monotonic() < deadline:
                if not selector.select(timeout=1):
                    continue
                line = process.stdout.readline()
                if not line:
                    raise RuntimeError("Codex app-server 已退出")
                envelope = Envelope.model_validate_json(line)
                if envelope.id == request.id:
                    if envelope.error is not None:
                        raise RuntimeError("Codex app-server 拒绝 MCP 状态查询")
                    return envelope
            raise TimeoutError("Codex MCP 状态查询超时")

        try:
            exchange(Request(id=1, method="initialize", params=InitializeParams()))
            process.stdin.write(Notification().model_dump_json() + "\n")
            process.stdin.flush()
            result = exchange(Request(id=2, method="mcpServerStatus/list", params=ListParams()))
            states = StatusResult.model_validate(result.result)
            market = next((item for item in states.data if item.name == "local-market"), None)
            return () if market is None else tuple(sorted(market.tools))
        finally:
            selector.close()
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
