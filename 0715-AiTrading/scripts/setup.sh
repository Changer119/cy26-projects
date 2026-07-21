#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

if ! command -v uv >/dev/null 2>&1; then
  echo "错误：未找到 uv，请先安装 uv。" >&2
  exit 1
fi

cd "${PROJECT_ROOT}"
uv sync --all-groups
