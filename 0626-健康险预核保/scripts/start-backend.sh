#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
    uv venv
fi

uv pip install -e . --quiet

if [ ! -f ".env" ]; then
    echo "❌ 缺少 .env 文件"
    exit 1
fi

mkdir -p logs

echo "启动后端 http://localhost:8000 ..."
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | tee logs/backend.log
