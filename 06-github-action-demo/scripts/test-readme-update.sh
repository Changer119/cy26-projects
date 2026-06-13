#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="$(mktemp -d)"
README_FILE="$WORK_DIR/README.md"

cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

cat > "$README_FILE" <<'MARKDOWN'
# GitHub Action Demo

<!-- AUTO_UPDATE_START -->
旧内容
<!-- AUTO_UPDATE_END -->
MARKDOWN

README_PATH="$README_FILE" "$ROOT_DIR/scripts/update-readme.sh"

if ! grep -q "最近更新时间" "$README_FILE"; then
  echo "README 没有写入最近更新时间"
  exit 1
fi

if grep -q "旧内容" "$README_FILE"; then
  echo "README 没有替换自动更新区块"
  exit 1
fi

if ! grep -q "由 GitHub Actions 定时更新" "$README_FILE"; then
  echo "README 没有写入工作流说明"
  exit 1
fi
