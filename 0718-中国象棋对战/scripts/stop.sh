#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

if [[ ! -f "${PID_FILE}" ]]; then
  echo "中国象棋对战 未运行。"
  exit 0
fi

PID="$(cat "${PID_FILE}")"
if kill -0 "${PID}" 2>/dev/null; then
  kill "${PID}"
fi
rm -f "${PID_FILE}"
echo "中国象棋对战 已停止。"
