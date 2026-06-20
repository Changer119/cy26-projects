#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# 启动 HTTP API，访问 http://127.0.0.1:8000/docs 查看交互式文档
uv run uvicorn weather.adapters.http:app --host 0.0.0.0 --port 8000 --reload
