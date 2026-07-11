#!/usr/bin/env bash
# 启动台风大屏服务（后台运行，日志输出到 logs/）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p logs

PID_FILE="logs/server.pid"
if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "服务已在运行 (PID $(cat "$PID_FILE"))，如需重启请先执行 scripts/stop.sh"
  exit 0
fi

echo "同步依赖..."
uv sync --quiet

echo "启动服务..."
nohup uv run python main.py >> logs/server.out 2>&1 &
echo $! > "$PID_FILE"
sleep 2

if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "启动成功 (PID $(cat "$PID_FILE"))"
  echo "大屏地址: http://localhost:8710"
else
  echo "启动失败，请查看 logs/server.out"
  exit 1
fi
