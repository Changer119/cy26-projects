#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
{
  if launchctl print "${MCP_DOMAIN}/${MCP_LABEL}" >/dev/null 2>&1; then
    echo "行情 MCP 已注册为用户常驻服务"
  fi
  curl --noproxy '*' --fail --silent --show-error --max-time 3 "${MCP_URL}/health"
  echo
} 2>&1 | tee "${PROJECT_ROOT}/logs/market-mcp/status.log"
