#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$(cd "$ROOT_DIR/.." && pwd)"
WORKFLOW_FILE="$REPO_DIR/.github/workflows/update-readme.yml"

if [[ ! -f "$WORKFLOW_FILE" ]]; then
  echo "父目录缺少 README 更新 workflow"
  exit 1
fi

if ! grep -q '06-github-action-demo/scripts/update-readme.sh' "$WORKFLOW_FILE"; then
  echo "workflow 没有调用子项目 README 更新脚本"
  exit 1
fi

if ! grep -q 'README_PATH="$GITHUB_WORKSPACE/README.md"' "$WORKFLOW_FILE"; then
  echo "workflow 没有把父目录 README 传给更新脚本"
  exit 1
fi
