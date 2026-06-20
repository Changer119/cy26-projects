#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# 用法示例: scripts/run_cli.sh 杭州 2026-06-20
# JSON 输出:  scripts/run_cli.sh 杭州 2026-06-20 --json
uv run weather "$@"
