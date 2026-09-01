#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
README_PATH="${README_PATH:-$ROOT_DIR/README.md}"
START_MARKER="<!-- AUTO_UPDATE_START -->"
END_MARKER="<!-- AUTO_UPDATE_END -->"

if [[ ! -f "$README_PATH" ]]; then
  echo "README 文件不存在: $README_PATH" >&2
  exit 1
fi

if ! grep -Fq "$START_MARKER" "$README_PATH" || ! grep -Fq "$END_MARKER" "$README_PATH"; then
  echo "README 缺少自动更新标记" >&2
  exit 1
fi

TIMESTAMP="$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
REPO_NAME="${GITHUB_REPOSITORY:-}"

if [[ -z "$REPO_NAME" ]]; then
  REMOTE_URL="$(git -C "$ROOT_DIR" config --get remote.origin.url || true)"
  REPO_NAME="$(printf '%s' "$REMOTE_URL" | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')"
fi

if [[ -z "$REPO_NAME" ]]; then
  REPO_NAME="unknown/unknown"
fi

TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

awk -v start="$START_MARKER" -v end="$END_MARKER" -v ts="$TIMESTAMP" -v repo="$REPO_NAME" '
  BEGIN { in_block = 0 }
  index($0, start) {
    print start
    print "- 最近更新时间：" ts
    print "- 由 GitHub Actions 定时更新，也可以通过 `workflow_dispatch` 手动触发。"
    print "- 当前仓库：`" repo "`"
    in_block = 1
    next
  }
  index($0, end) {
    print end
    in_block = 0
    next
  }
  !in_block { print }
' "$README_PATH" > "$TMP_FILE"

mv "$TMP_FILE" "$README_PATH"

