#!/usr/bin/env bash
# 停止前端 Next.js dev server
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"
PID_FILE="${LOG_DIR}/frontend.pid"

if [[ ! -f "${PID_FILE}" ]]; then
  echo "前端服务未运行。"
  exit 0
fi

PID="$(cat "${PID_FILE}")"
if kill -0 "${PID}" 2>/dev/null; then
  kill "${PID}"
  echo "前端服务已停止。"
else
  echo "前端服务未运行（进程已不存在）。"
fi
rm -f "${PID_FILE}"
