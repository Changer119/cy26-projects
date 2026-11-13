#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/common.sh"
MCP_LABEL="com.local.ai-trading.market-mcp"
MCP_DOMAIN="gui/${UID}"
MCP_TARGET="${HOME}/Library/LaunchAgents/${MCP_LABEL}.plist"
MCP_PORT="${AI_TRADING_MCP_PORT:-8766}"
MCP_URL="http://127.0.0.1:${MCP_PORT}"
mkdir -p "${PROJECT_ROOT}/logs/market-mcp"

wait_for_mcp() {
  for _attempt in {1..60}; do
    if curl --noproxy '*' --fail --silent --max-time 2 "${MCP_URL}/health" >/dev/null; then
      echo "行情 MCP 已就绪：${MCP_URL}/mcp"
      return 0
    fi
    sleep 0.5
  done
  echo "行情 MCP 未就绪，请检查 logs/market-mcp/" >&2
  return 1
}
