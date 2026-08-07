#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

if [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
  echo "中国象棋对战 正在运行，PID=$(cat "${PID_FILE}")，http://localhost:${PORT}"
  exit 0
fi

echo "中国象棋对战 未运行。"
exit 1
