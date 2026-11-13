# 本机 Agent 行情 MCP 配置

2026-10-30，已为本机确认可运行的四个 Agent 注册用户级 `local-market` 行情 MCP，统一连接 `http://127.0.0.1:8766/mcp`，并写入对应的本地访问令牌。

## 配置位置与原生验证

| Agent | 用户级配置文件 | 实际验证结果 |
|---|---|---|
| Codex | `/Users/jiangfachang/.codex/config.toml` | `codex mcp get local-market --json` 读取成功；app-server 的只读 MCP 状态接口发现三个工具 |
| Claude Code | `/Users/jiangfachang/.claude.json` | `claude mcp get local-market` 报告 `Connected`，作用域为 user |
| Hermes | `/Users/jiangfachang/.hermes/config.yaml` | `hermes mcp test local-market` 连接成功，发现三个工具 |
| OpenCode | `/Users/jiangfachang/.config/opencode/opencode.json` | `opencode mcp list` 报告 `local-market connected` |

三个工具为 `get_daily_bar`、`get_daily_history`、`check_data_sources`。现有 Agent 进程可能缓存工具列表，已打开的客户端需要重载 MCP 或重新启动后再使用；没有强制停止用户正在运行的 Agent。

Gemini、Cursor、Kiro、Trae 的相关目录存在，但本次没有发现其可执行客户端，因此未修改这些目录，也未声称它们已经接通。

## 配置保护

修改前完整备份到：

```text
/Users/jiangfachang/Code/AICoding/cy26-projects/0715-AiTrading/data/market-mcp/agent-backups/20261030-223854-189658/
```

所有原有 MCP 条目及其他设置均通过结构化比较确认保留。TOML、YAML 使用保留格式的解析器更新；JSON 保留原有字段和值。四个全局配置及备份文件均采用仅当前用户可读写的权限，令牌没有回显。

配置脚本可重复运行：内容相同时跳过，不添加重复条目。备份目录与生成的客户端配置位于项目已忽略的私密数据目录，不提交到 Git。

## 复核与同步

在项目目录内运行：

```bash
scripts/mcp/status.sh
scripts/mcp_clients/verify.sh
```

验证脚本通过四个客户端的原生命令、Codex app-server 只读接口，以及真实 HTTP MCP 调用进行复核，不创建 Agent 会话，不调用模型。输出在写入日志前隐藏本地访问令牌。

更换本地访问令牌后，同步到四个客户端：

```bash
scripts/mcp/start.sh
scripts/mcp_clients/configure.sh
scripts/mcp_clients/verify.sh
```

同步后，让已打开的 Agent 重载 MCP 配置。日志位于 `logs/market-mcp/configure-clients.log` 和 `logs/market-mcp/verify-clients.log`。

## 本次取数和回归

HTTP legacy MCP 客户端实际取得 `600584.SH` 在 2026-10-28 的行情，来源 Tushare，收盘价 `55.41`、成交量 `67589920` 股。该验收针对具体股票和日期，不代表所有历史区间和上游额度均可用。

项目检查通过：207 项后端测试、7 项前端测试、严格类型检查、格式及目录约束、前端生产构建。

## 配置依据

- [Codex 官方 MCP 配置](https://developers.openai.com/codex/mcp)
- [OpenCode 官方 MCP 配置](https://opencode.ai/docs/mcp-servers/)
- Claude Code 以本机 `claude mcp` 帮助及原生连接检查为准。
- Hermes 以本机 `hermes_cli/mcp_config.py`、`tools/mcp_tool.py` 和原生测试为准。
