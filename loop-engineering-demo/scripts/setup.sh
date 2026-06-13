#!/usr/bin/env bash
# 安装项目依赖（包含 dev 依赖）
set -euo pipefail
cd "$(dirname "$0")/.."

uv sync
