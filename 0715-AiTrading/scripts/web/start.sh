#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WEB_ROOT="${PROJECT_ROOT}/web"
PID_FILE="${PROJECT_ROOT}/logs/web-app.pid"

mkdir -p "${PROJECT_ROOT}/logs"
if [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
  echo "Web 仪表盘已运行，PID=$(cat "${PID_FILE}")"
  exit 0
fi
if [[ ! -d "${WEB_ROOT}/node_modules" ]]; then
  "${PROJECT_ROOT}/scripts/web/setup.sh"
fi
cd "${WEB_ROOT}"
nohup npm run dev -- --host 127.0.0.1 --port 5173 >"${PROJECT_ROOT}/logs/web-app.log" 2>&1 &
echo "$!" >"${PID_FILE}"
for _attempt in {1..20}; do
  if curl --fail --silent http://127.0.0.1:5173/ >/dev/null; then
    echo "Web 仪表盘已启动，PID=$(cat "${PID_FILE}")，地址=http://127.0.0.1:5173"
    exit 0
  fi
  sleep 0.25
done
echo "Web 仪表盘启动失败，请查看 logs/web-app.log" >&2
rm -f "${PID_FILE}"
exit 1
