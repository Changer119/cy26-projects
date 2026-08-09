#!/usr/bin/env bash
# 手动触发 open-code-review：审查当前工作区改动（staged+unstaged+untracked）。
# 用法：
#   ./scripts/review.sh                      # 审查当前工作区改动
#   ./scripts/review.sh --from main --to dev # 审查分支 diff（透传给 ocr review 的额外参数）
set -euo pipefail

if ! command -v ocr >/dev/null 2>&1; then
  echo "错误：未安装 ocr CLI（npm install -g @alibaba-group/open-code-review）" >&2
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"

if [ "$#" -eq 0 ] \
  && git -C "$REPO_ROOT" diff --cached --quiet \
  && git -C "$REPO_ROOT" diff --quiet \
  && [ -z "$(git -C "$REPO_ROOT" ls-files --others --exclude-standard | head -n 1)" ]; then
  echo "工作区没有改动，无需 review"
  exit 0
fi

if ! ocr review \
  --audience agent \
  --repo "$REPO_ROOT" \
  --background "手动触发的 review" \
  "$@"; then
  echo "错误：ocr review 执行失败，请检查上方错误输出" >&2
  exit 1
fi
