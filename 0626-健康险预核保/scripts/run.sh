#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# 确保虚拟环境存在
if [ ! -d ".venv" ]; then
    echo "初始化虚拟环境..."
    uv venv
fi

# 安装依赖
uv pip install -e . --quiet

# 确保 .env 存在
if [ ! -f ".env" ]; then
    echo "❌ 缺少 .env 文件，请先复制 .env.example 并填写配置："
    echo "   cp .env.example .env"
    exit 1
fi

# 确保 logs 目录存在
mkdir -p logs

# 启动
echo "启动预核保助手..."
uv run python main.py
