#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
PID_FILE="${PROJECT_ROOT}/logs/ai-trading.pid"

if [[ ! -f "${PID_FILE}" ]]; then
  echo "AI Trading 未运行。"
  exit 0
fi

PID="$(cat "${PID_FILE}")"
if kill -0 "${PID}" 2>/dev/null; then
  kill "${PID}"
fi
rm -f "${PID_FILE}"
echo "AI Trading 已停止。"
