#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
"${PROJECT_ROOT}/scripts/mcp/stop.sh"
rm -f "${MCP_TARGET}"
echo "行情 MCP 常驻服务已卸载，配置和日志保留"
