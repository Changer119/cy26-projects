#!/usr/bin/env bash
# 启动前端 Next.js dev server（内部客服 chatbot 聊天界面）
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"
LOG_DIR="${PROJECT_ROOT}/logs"
PID_FILE="${LOG_DIR}/frontend.pid"
PORT="${FRONTEND_PORT:-3000}"

mkdir -p "${LOG_DIR}"

if [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
  echo "前端服务已在运行：http://localhost:${PORT}"
  exit 0
fi

cd "${FRONTEND_DIR}"

if [[ ! -d node_modules ]]; then
  echo "首次运行，安装前端依赖..."
  npm install 2>&1 | tee "${LOG_DIR}/frontend-install.log"
fi

nohup npm run dev -- --port "${PORT}" >"${LOG_DIR}/frontend.log" 2>&1 &
echo "$!" >"${PID_FILE}"

for _ in {1..60}; do
  if curl --silent --fail "http://localhost:${PORT}" >/dev/null; then
    echo "前端服务已启动：http://localhost:${PORT}"
    exit 0
  fi
  sleep 0.5
done

echo "启动超时，请查看 ${LOG_DIR}/frontend.log" >&2
exit 1
