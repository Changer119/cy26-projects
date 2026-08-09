#!/usr/bin/env bash
# 启用 scripts/git-hooks 作为本仓库的 git hooks 目录（含 open-code-review pre-commit hook）
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

if [ ! -f scripts/git-hooks/pre-commit ]; then
  echo "错误：scripts/git-hooks/pre-commit 不存在，安装中止" >&2
  exit 1
fi
chmod +x scripts/git-hooks/pre-commit

if ! git config core.hooksPath scripts/git-hooks; then
  echo "错误：设置 core.hooksPath 失败，请检查 git 配置" >&2
  exit 1
fi

echo "已启用 git hooks 目录：scripts/git-hooks"
echo "跳过单次 review：SKIP_OCR_REVIEW=1 git commit ..."
echo "彻底跳过全部 hooks：git commit --no-verify"
