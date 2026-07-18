#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
ensure_environment

if [[ ! -f "${PROJECT_ROOT}/web/dist/index.html" ]]; then
  "${PROJECT_ROOT}/scripts/web/build.sh"
fi

PID_FILE="${PROJECT_ROOT}/logs/ai-trading.pid"
HEALTH_URL="http://127.0.0.1:8765/api/health"

wait_until_ready() {
  local pid="$1"
  for _attempt in {1..40}; do
    if ! kill -0 "${pid}" 2>/dev/null; then
      return 1
    fi
    if curl --fail --silent "${HEALTH_URL}" >/dev/null; then
      return 0
    fi
    sleep 0.25
  done
  return 1
}

if [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
  PID="$(cat "${PID_FILE}")"
  if wait_until_ready "${PID}"; then
    echo "AI Trading 已运行，PID=${PID}，地址=http://127.0.0.1:8765"
    exit 0
  fi
  echo "AI Trading 进程存在但健康检查失败，请查看 logs/app.log" >&2
  exit 1
fi

if curl --fail --silent "${HEALTH_URL}" >/dev/null; then
  echo "AI Trading 已由常驻服务运行，地址=http://127.0.0.1:8765"
  exit 0
fi

cd "${PROJECT_ROOT}"
nohup uv run uvicorn ai_trading.main:app --host 127.0.0.1 --port 8765 --workers 1 \
  >>"${PROJECT_ROOT}/logs/app.log" 2>&1 &
echo $! >"${PID_FILE}"
PID="$!"
if wait_until_ready "${PID}"; then
  echo "AI Trading 已启动，PID=${PID}，地址=http://127.0.0.1:8765"
  exit 0
fi
kill "${PID}" 2>/dev/null || true
rm -f "${PID_FILE}"
echo "AI Trading 启动失败，请查看 logs/app.log" >&2
exit 1
