#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PID_FILE="${PROJECT_ROOT}/logs/web-app.pid"

if [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
  echo "Web 仪表盘运行中，PID=$(cat "${PID_FILE}")，地址=http://127.0.0.1:5173"
  exit 0
fi
echo "Web 仪表盘未运行"
exit 1
