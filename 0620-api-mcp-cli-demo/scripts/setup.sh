#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> 创建虚拟环境并安装依赖 (uv sync)"
uv sync

if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> 已生成 .env，请填入 ANTHROPIC_API_KEY"
fi

echo "==> 完成"
