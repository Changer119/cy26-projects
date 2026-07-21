#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PID_FILE="${PROJECT_ROOT}/logs/web-app.pid"

if [[ ! -f "${PID_FILE}" ]]; then
  echo "Web 仪表盘未运行"
  exit 0
fi
PID="$(cat "${PID_FILE}")"
if kill -0 "${PID}" 2>/dev/null; then
  kill "${PID}"
fi
rm -f "${PID_FILE}"
echo "Web 仪表盘已停止"
