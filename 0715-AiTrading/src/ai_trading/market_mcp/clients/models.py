"""只描述 MCP 字段；其余设置原样保留。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class PreservedModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    __pydantic_extra__: dict[str, JsonValue] = Field(init=False, repr=False)


class ServerEntry(PreservedModel):
    type: str | None = None
    url: str | None = None
    headers: dict[str, str] | None = None
    http_headers: dict[str, str] | None = None
    enabled: bool | None = None
    startup_timeout_sec: int | None = None
    tool_timeout_sec: int | None = None
    connect_timeout: int | None = None
    timeout: int | None = None
    skip_preflight: bool | None = None


class AgentConfiguration(PreservedModel):
    claude_servers: dict[str, ServerEntry] = Field(default_factory=dict, alias="mcpServers")
    codex_servers: dict[str, ServerEntry] = Field(default_factory=dict, alias="mcp_servers")
    opencode_servers: dict[str, ServerEntry] = Field(default_factory=dict, alias="mcp")


class ConfiguredAgent(BaseModel):
    name: Literal["Codex", "Claude Code", "Hermes", "OpenCode"]
    path: str
    format: Literal["toml", "json", "yaml"]
    server: ServerEntry


class ConfigurationRecord(BaseModel):
    name: str
    path: str
    changed: bool
    backup: str | None
    preserved_existing_servers: bool
