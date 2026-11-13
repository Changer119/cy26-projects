#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
ensure_environment
{
  mkdir -p "${HOME}/Library/LaunchAgents"
  if ! launchctl print "${MCP_DOMAIN}/${MCP_LABEL}" >/dev/null 2>&1 && \
    lsof -nP -iTCP:"${MCP_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "端口 ${MCP_PORT} 已被其他服务占用" >&2
    exit 1
  fi
  sed -e "s|__PROJECT_ROOT__|${PROJECT_ROOT}|g" -e "s|__MCP_PORT__|${MCP_PORT}|g" \
    "${PROJECT_ROOT}/deploy/launchd/${MCP_LABEL}.plist.template" >"${MCP_TARGET}"
  plutil -lint "${MCP_TARGET}"
  launchctl bootout "${MCP_DOMAIN}" "${MCP_TARGET}" >/dev/null 2>&1 || true
  launchctl bootstrap "${MCP_DOMAIN}" "${MCP_TARGET}"
  wait_for_mcp
  echo "已安装用户登录后自动启动及退出后自动拉起的行情 MCP"
  echo "客户端配置：${PROJECT_ROOT}/data/market-mcp/client.json（含本地访问令牌）"
} 2>&1 | tee "${PROJECT_ROOT}/logs/market-mcp/install.log"
