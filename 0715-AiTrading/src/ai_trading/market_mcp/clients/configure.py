"""备份并原子更新四个 Agent 的全局 MCP 配置，不回显凭据。"""

import os
from datetime import datetime
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo

import tomlkit
import typer
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from tomlkit.container import OutOfOrderTableProxy
from tomlkit.items import Table

from ai_trading.config import Settings
from ai_trading.logging_config import configure_logging
from ai_trading.market_mcp.auth import local_token
from ai_trading.market_mcp.clients.models import (
    AgentConfiguration,
    ConfigurationRecord,
    ConfiguredAgent,
    ServerEntry,
)

SERVER = "local-market"


def targets(root: Path, user_root: Path) -> tuple[ConfiguredAgent, ...]:
    settings = Settings()
    key = local_token(root, settings.mcp_port)
    url = f"http://127.0.0.1:{settings.mcp_port}/mcp"
    headers = {"Authorization": f"Bearer {key.get_secret_value()}"}
    return (
        ConfiguredAgent(
            name="Codex",
            path=str(user_root / ".codex/config.toml"),
            format="toml",
            server=ServerEntry(
                url=url,
                http_headers=headers,
                enabled=True,
                startup_timeout_sec=30,
                tool_timeout_sec=120,
            ),
        ),
        ConfiguredAgent(
            name="Claude Code",
            path=str(user_root / ".claude.json"),
            format="json",
            server=ServerEntry(type="http", url=url, headers=headers),
        ),
        ConfiguredAgent(
            name="Hermes",
            path=str(user_root / ".hermes/config.yaml"),
            format="yaml",
            server=ServerEntry(
                url=url,
                headers=headers,
                enabled=True,
                connect_timeout=30,
                timeout=120,
                skip_preflight=True,
            ),
        ),
        ConfiguredAgent(
            name="OpenCode",
            path=str(user_root / ".config/opencode/opencode.json"),
            format="json",
            server=ServerEntry(type="remote", url=url, headers=headers, enabled=True),
        ),
    )


def _yaml() -> YAML:
    parser = YAML()
    parser.preserve_quotes = True
    return parser


def read_configuration(text: str, kind: str) -> AgentConfiguration:
    if kind == "json":
        return AgentConfiguration.model_validate_json(text)
    if kind == "toml":
        return AgentConfiguration.model_validate(tomlkit.parse(text).unwrap())
    return AgentConfiguration.model_validate(_yaml().load(text))


def _servers(config: AgentConfiguration, name: str) -> dict[str, ServerEntry]:
    if name == "Claude Code":
        return config.claude_servers
    if name == "OpenCode":
        return config.opencode_servers
    return config.codex_servers


def update_text(text: str, target: ConfiguredAgent) -> str:
    parsed = read_configuration(text, target.format)
    _servers(parsed, target.name)[SERVER] = target.server
    if target.format == "json":
        # 显式标记当前字典字段，确保原本缺少 mcp 字段的配置也会写入。
        if target.name == "Claude Code":
            parsed.claude_servers = parsed.claude_servers
        else:
            parsed.opencode_servers = parsed.opencode_servers
        return parsed.model_dump_json(by_alias=True, exclude_unset=True, indent=2) + "\n"
    entry = target.server.model_dump(exclude_unset=True)
    if target.format == "toml":
        document = tomlkit.parse(text)
        section = document.get("mcp_servers")
        if section is None:
            section = tomlkit.table()
            document.add("mcp_servers", section)
        if not isinstance(section, (Table, OutOfOrderTableProxy)):
            raise ValueError("Codex mcp_servers 结构不支持安全修改")
        section[SERVER] = tomlkit.item(entry)
        return tomlkit.dumps(document)
    parser = _yaml()
    document_yaml = parser.load(text)
    if not isinstance(document_yaml, CommentedMap):
        raise ValueError("Hermes 配置必须是 YAML 映射")
    section_yaml = document_yaml.get("mcp_servers")
    if section_yaml is None:
        section_yaml = CommentedMap()
        document_yaml["mcp_servers"] = section_yaml
    if not isinstance(section_yaml, CommentedMap):
        raise ValueError("Hermes mcp_servers 结构不支持安全修改")
    section_yaml[SERVER] = CommentedMap(entry)
    output = StringIO()
    parser.dump(document_yaml, output)
    return output.getvalue()


def write_private(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    os.chmod(temporary_path, 0o600)
    os.replace(temporary_path, path)


def configure_one(target: ConfiguredAgent, backup_dir: Path) -> ConfigurationRecord:
    path = Path(target.path)
    for _ in range(3):
        before = path.read_text(encoding="utf-8")
        original = read_configuration(before, target.format)
        candidate = update_text(before, target)
        after = read_configuration(candidate, target.format)
        # 对比完整配置：唯一允许的差异是当前行情 MCP。
        _servers(original, target.name).pop(SERVER, None)
        _servers(after, target.name).pop(SERVER, None)
        # 新增空 mcp 容器时，统一字段集合后比较数据。
        if original.model_dump() != after.model_dump():
            raise ValueError(f"{target.name} 检测到行情 MCP 之外的配置变化，已停止写入")
        current = read_configuration(before, target.format)
        if _servers(current, target.name).get(SERVER) == target.server:
            return ConfigurationRecord(
                name=target.name,
                path=str(path),
                changed=False,
                backup=None,
                preserved_existing_servers=True,
            )
        if path.read_text(encoding="utf-8") != before:
            continue
        backup = backup_dir / f"{target.name.replace(' ', '-').lower()}.{target.format}"
        write_private(backup, before)
        write_private(path, candidate)
        return ConfigurationRecord(
            name=target.name,
            path=str(path),
            changed=True,
            backup=str(backup),
            preserved_existing_servers=True,
        )
    raise RuntimeError(f"{target.name} 配置正在被其他进程修改，请稍后重试")


def main() -> None:
    settings = Settings()
    configure_logging(settings.project_root / "logs" / "market-mcp", settings.log_level)
    stamp = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S-%f")
    backup_dir = settings.project_root / "data" / "market-mcp" / "agent-backups" / stamp
    backup_dir.mkdir(parents=True, mode=0o700)
    for target in targets(settings.project_root, Path.home()):
        record = configure_one(target, backup_dir)
        typer.echo(record.model_dump_json())


if __name__ == "__main__":
    main()
