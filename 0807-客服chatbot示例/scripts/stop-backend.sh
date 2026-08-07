#!/usr/bin/env bash
# 停止客服 chatbot 后端服务。
# 用法: ./scripts/stop-backend.sh
set -euo pipefail

PORT="${APP_PORT:-8000}"
# 按命令行特征匹配整个进程树（含 uv run 包装出的 uvicorn 子进程），
# 只用 PID 文件在 uv 场景下可能杀不干净子进程。
MATCH_PATTERN="uvicorn main:app.*--port $PORT"

if ! pgrep -f "$MATCH_PATTERN" >/dev/null 2>&1; then
  echo "后端服务未在运行 (端口 $PORT)"
  exit 0
fi

pkill -f "$MATCH_PATTERN"
sleep 1

if pgrep -f "$MATCH_PATTERN" >/dev/null 2>&1; then
  echo "进程未响应 SIGTERM，强制终止..."
  pkill -9 -f "$MATCH_PATTERN" || true
fi

echo "后端服务已停止 (端口 $PORT)"
