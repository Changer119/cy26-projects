#!/usr/bin/env bash
# 查看桥接服务运行状态，并 tail 最近日志
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$DIR/config/bridge.env"

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "桥接服务运行中，PID=$(cat "$PID_FILE")"
else
  echo "桥接服务未运行"
fi

echo
echo "--- lark-cli 事件守护进程状态 ---"
lark-cli --profile "$LARK_PROFILE" event status --current

echo
echo "--- 已建立的会话（chat_id -> session_id）---"
if [[ -d "$SESSION_DIR" ]] && [[ -n "$(ls -A "$SESSION_DIR" 2>/dev/null)" ]]; then
  for f in "$SESSION_DIR"/*.session_id; do
    echo "$(basename "$f" .session_id) -> $(cat "$f")"
  done
else
  echo "（暂无）"
fi

echo
echo "--- 最近 20 行日志 (logs/bridge.log) ---"
tail -n 20 "$LOG_DIR/bridge.log" 2>/dev/null || echo "（暂无日志）"
