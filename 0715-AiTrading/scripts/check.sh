#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
ensure_environment

cd "${PROJECT_ROOT}"
{
  while IFS= read -r -d '' script; do
    bash -n "${script}"
  done < <(find scripts -type f -name '*.sh' -print0)
  while IFS= read -r -d '' file; do
    lines="$(wc -l <"${file}")"
    if (( lines > 300 )); then
      echo "错误：动态语言文件超过 300 行：${file} (${lines})" >&2
      exit 1
    fi
  done < <(find src tests web/src -type f \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' \) -print0)
  while IFS= read -r directory; do
    files="$(find "${directory}" -maxdepth 1 -type f | wc -l | tr -d ' ')"
    if (( files > 8 )); then
      echo "错误：目录直接文件超过 8 个：${directory} (${files})" >&2
      exit 1
    fi
  done < <(find src tests scripts web/src -type d)
  plutil -lint deploy/launchd/com.local.ai-trading.plist.template
  uv run ruff format --check src tests
  uv run ruff check src tests
  uv run mypy src
  uv run pytest
  "${PROJECT_ROOT}/scripts/web/test.sh"
  "${PROJECT_ROOT}/scripts/web/build.sh"
} 2>&1 | tee "${PROJECT_ROOT}/logs/check.log"
