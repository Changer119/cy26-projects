#!/usr/bin/env bash
# 启动客服 chatbot 后端服务（FastAPI，通过 uv 管理与运行）。
# 用法: ./scripts/start-backend.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
LOG_DIR="$BACKEND_DIR/logs"
PORT="${APP_PORT:-8000}"
# uv run 会 fork 出真正的 uvicorn 子进程，用命令行特征匹配整个进程树，
# 避免只杀掉 uv 包装进程、留下孤儿 uvicorn 继续占用端口。
MATCH_PATTERN="uvicorn main:app.*--port $PORT"

if [ ! -d "$BACKEND_DIR" ]; then
  echo "错误: 未找到后端目录 $BACKEND_DIR" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "错误: 未找到 uv 命令，请先安装 uv (https://docs.astral.sh/uv/)" >&2
  exit 1
fi

mkdir -p "$LOG_DIR"

if pgrep -f "$MATCH_PATTERN" >/dev/null 2>&1; then
  echo "后端服务已在运行 (端口 $PORT)，如需重启请先执行 stop-backend.sh"
  exit 0
fi

if [ ! -f "$BACKEND_DIR/.env" ]; then
  echo "提示: 未找到 backend/.env，DeepSeek 相关配置将为空，/api/chat 调用会返回明确报错。"
  echo "      如需真实联通 DeepSeek，请复制 backend/.env.example 为 backend/.env 并填写 DEEPSEEK_API_KEY。"
fi

echo "正在通过 uv 同步依赖..."
(cd "$BACKEND_DIR" && uv sync)

echo "正在启动后端服务 (端口 $PORT)..."
(cd "$BACKEND_DIR" && nohup uv run uvicorn main:app --host 0.0.0.0 --port "$PORT" \
  >> "$LOG_DIR/uvicorn.out.log" 2>&1 &)

sleep 2
if pgrep -f "$MATCH_PATTERN" >/dev/null 2>&1; then
  echo "后端服务已启动，监听端口 $PORT"
  echo "健康检查: curl http://localhost:$PORT/api/health"
  echo "日志文件: $LOG_DIR/uvicorn.out.log , $LOG_DIR/backend.log"
else
  echo "错误: 后端服务启动失败，请查看日志 $LOG_DIR/uvicorn.out.log" >&2
  exit 1
fi
