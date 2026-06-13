#!/usr/bin/env bash
# 模拟 CI 流水线：lint + 测试，结果写入 logs/，并以退出码反映整体成败
set -uo pipefail
cd "$(dirname "$0")/.."

mkdir -p logs

echo "==> Lint (ruff)"
uv run ruff check src tests 2>&1 | tee logs/lint.log
lint_status=${PIPESTATUS[0]}

echo ""
echo "==> Tests (pytest)"
uv run pytest -v 2>&1 | tee logs/test.log
test_status=${PIPESTATUS[0]}

echo ""
if [ "$lint_status" -eq 0 ] && [ "$test_status" -eq 0 ]; then
    echo "CI 通过"
    exit 0
else
    echo "CI 失败 (lint=$lint_status, test=$test_status)"
    exit 1
fi
