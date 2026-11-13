#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
if [[ ! -f "${MCP_TARGET}" ]]; then
  exec "${PROJECT_ROOT}/scripts/mcp/install.sh"
fi
{
  if ! launchctl print "${MCP_DOMAIN}/${MCP_LABEL}" >/dev/null 2>&1; then
    launchctl bootstrap "${MCP_DOMAIN}" "${MCP_TARGET}"
  fi
  launchctl kickstart -k "${MCP_DOMAIN}/${MCP_LABEL}"
  wait_for_mcp
} 2>&1 | tee "${PROJECT_ROOT}/logs/market-mcp/start.log"
