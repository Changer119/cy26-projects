#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
README_PATH="$ROOT_DIR/README.md"
TMP_DIR="$(mktemp -d)"
TMP_README="$TMP_DIR/README.md"

cleanup() {
  rm -rf "$TMP_DIR"
}

trap cleanup EXIT

if [[ ! -f "$README_PATH" ]]; then
  echo "README 不存在: $README_PATH" >&2
  exit 1
fi

cp "$README_PATH" "$TMP_README"

README_PATH="$TMP_README" \
GITHUB_REPOSITORY="Changer119/cy26-projects" \
bash "$ROOT_DIR/scripts/update-readme.sh"

grep -Fq "<!-- AUTO_UPDATE_START -->" "$TMP_README"
grep -Fq "<!-- AUTO_UPDATE_END -->" "$TMP_README"
grep -Fq "最近更新时间：" "$TMP_README"
grep -Fq '当前仓库：`Changer119/cy26-projects`' "$TMP_README"

echo "README 自动更新脚本检查通过"

