#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$(cd "$ROOT_DIR/.." && pwd)"
README_WORKFLOW_FILE="$REPO_DIR/.github/workflows/update-readme.yml"
PUSH_TEST_WORKFLOW_FILE="$REPO_DIR/.github/workflows/test-on-push.yml"

if [[ ! -f "$README_WORKFLOW_FILE" ]]; then
  echo "父目录缺少 README 更新 workflow"
  exit 1
fi

if ! grep -q '06-github-action-demo/scripts/update-readme.sh' "$README_WORKFLOW_FILE"; then
  echo "workflow 没有调用子项目 README 更新脚本"
  exit 1
fi

if ! grep -q 'README_PATH="$GITHUB_WORKSPACE/README.md"' "$README_WORKFLOW_FILE"; then
  echo "workflow 没有把父目录 README 传给更新脚本"
  exit 1
fi

if [[ ! -f "$PUSH_TEST_WORKFLOW_FILE" ]]; then
  echo "父目录缺少 push 后自动跑测试 workflow"
  exit 1
fi

if ! grep -q '^  push:' "$PUSH_TEST_WORKFLOW_FILE"; then
  echo "push 测试 workflow 没有监听 push 事件"
  exit 1
fi

if ! grep -q 'bash 06-github-action-demo/scripts/test.sh' "$PUSH_TEST_WORKFLOW_FILE"; then
  echo "push 测试 workflow 没有调用子项目测试脚本"
  exit 1
fi
