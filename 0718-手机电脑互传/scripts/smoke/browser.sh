#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PORT="${PHONE2COMPUTER_PORT:-18765}"
SESSION="phone2computer-smoke"
trap 'agent-browser --session "${SESSION}" close >/dev/null 2>&1 || true' EXIT

agent-browser --session "${SESSION}" open "http://127.0.0.1:${PORT}/admin" >/dev/null
agent-browser --session "${SESSION}" set viewport 1440 1000 >/dev/null
agent-browser --session "${SESSION}" wait --load networkidle >/dev/null
agent-browser --session "${SESSION}" snapshot -i
agent-browser --session "${SESSION}" screenshot "${PROJECT_ROOT}/logs/admin-page.png" >/dev/null

CONFIG_JSON="$(curl --silent --show-error --fail "http://127.0.0.1:${PORT}/api/admin/config")"
UPLOAD_URL="$(printf '%s' "${CONFIG_JSON}" | jq -r '.upload_url')"

agent-browser --session "${SESSION}" set viewport 430 932 >/dev/null
agent-browser --session "${SESSION}" open "${UPLOAD_URL}" >/dev/null
agent-browser --session "${SESSION}" wait --load networkidle >/dev/null
agent-browser --session "${SESSION}" snapshot -i
agent-browser --session "${SESSION}" screenshot "${PROJECT_ROOT}/logs/mobile-page.png" >/dev/null

PAGE_ERRORS="$(agent-browser --session "${SESSION}" errors)"
if [[ -n "${PAGE_ERRORS}" && "${PAGE_ERRORS}" != *"No page errors"* ]]; then
  echo "浏览器验收失败：页面存在 JavaScript 错误" >&2
  echo "${PAGE_ERRORS}" >&2
  exit 1
fi

echo "浏览器验收通过：Mac 管理页与手机上传页均正常。"
