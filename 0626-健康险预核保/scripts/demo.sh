#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
    echo "初始化虚拟环境..."
    uv venv
fi

uv pip install -e . --quiet

if [ ! -f ".env" ]; then
    echo "❌ 缺少 .env 文件，请先复制 .env.example 并填写配置"
    exit 1
fi

mkdir -p logs

uv run python demo.py 2>&1 | tee logs/demo.log
