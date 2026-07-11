#!/usr/bin/env bash
# 停止台风大屏服务
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$ROOT/logs/server.pid"

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  kill "$(cat "$PID_FILE")"
  rm -f "$PID_FILE"
  echo "服务已停止"
else
  rm -f "$PID_FILE"
  echo "服务未在运行"
fi
