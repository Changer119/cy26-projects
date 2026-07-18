#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

if ! command -v go >/dev/null 2>&1; then
  brew install go
fi

cd "${PROJECT_ROOT}/web"
npm install

cd "${PROJECT_ROOT}"
go mod tidy
