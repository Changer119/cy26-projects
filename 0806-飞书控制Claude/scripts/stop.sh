#!/usr/bin/env bash
# 停止桥接服务（前台或 LaunchAgent 常驻均可用）
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$DIR/config/bridge.env"

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    echo "已发送停止信号 (PID=$PID)"
  else
    echo "PID 文件存在但进程未运行，清理残留文件"
  fi
  rm -f "$PID_FILE"
else
  echo "未找到运行中的桥接服务 PID 文件"
fi

# 顺带停掉底层的 lark-cli 事件订阅守护进程
lark-cli --profile "$LARK_PROFILE" event stop --force >/dev/null 2>&1 || true
echo "已停止 lark-cli 事件订阅"
