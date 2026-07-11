#!/usr/bin/env bash
# 查看服务状态与最新数据刷新情况
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$ROOT/logs/server.pid"

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "服务运行中 (PID $(cat "$PID_FILE")) → http://localhost:8710"
  echo "--- 健康检查 ---"
  curl -s http://localhost:8710/api/health || true
  echo
  echo "--- 最近日志 ---"
  tail -n 5 "$ROOT/logs/app.log" 2>/dev/null || echo "暂无日志"
else
  echo "服务未在运行"
fi
