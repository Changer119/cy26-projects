#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
{
  if launchctl print "${MCP_DOMAIN}/${MCP_LABEL}" >/dev/null 2>&1; then
    launchctl bootout "${MCP_DOMAIN}" "${MCP_TARGET}"
  fi
  echo "行情 MCP 已停止，运行 start.sh 可恢复"
} 2>&1 | tee "${PROJECT_ROOT}/logs/market-mcp/stop.log"
