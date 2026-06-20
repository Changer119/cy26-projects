#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# 以 stdio 方式启动 MCP server，供 Claude Desktop / Cursor 等客户端接入
uv run python -m weather.adapters.mcp
