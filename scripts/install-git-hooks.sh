#!/usr/bin/env bash
# 启用 scripts/git-hooks 作为本仓库的 git hooks 目录（含 open-code-review pre-commit hook）
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

chmod +x scripts/git-hooks/pre-commit
git config core.hooksPath scripts/git-hooks

echo "已启用 git hooks 目录：scripts/git-hooks"
echo "跳过单次 review：SKIP_OCR_REVIEW=1 git commit ..."
echo "彻底跳过全部 hooks：git commit --no-verify"
