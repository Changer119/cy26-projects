#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

if [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
  echo "中国象棋对战 已在运行：http://localhost:${PORT}"
  exit 0
fi

cd "${FRONTEND_DIR}"
if [[ ! -d node_modules ]]; then
  npm install 2>&1 | tee "${LOG_DIR}/install.log"
fi

nohup npm run dev -- --port "${PORT}" >"${LOG_DIR}/frontend.log" 2>&1 &
echo "$!" >"${PID_FILE}"

for _ in {1..60}; do
  if curl --silent --fail "http://localhost:${PORT}" >/dev/null; then
    echo "中国象棋对战 已启动：http://localhost:${PORT}"
    exit 0
  fi
  sleep 0.5
done

echo "启动失败，请查看 ${LOG_DIR}/frontend.log" >&2
exit 1
