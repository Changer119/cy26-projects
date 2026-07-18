#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "${PROJECT_ROOT}"
{
  while IFS= read -r -d '' script; do
    bash -n "${script}"
  done < <(find scripts -type f -name '*.sh' -print0)

  while IFS= read -r -d '' file; do
    lines="$(wc -l <"${file}")"
    limit=400
    case "${file}" in
      *.ts|*.tsx) limit=300 ;;
    esac
    if (( lines > limit )); then
      echo "错误：${file} 超过 ${limit} 行（${lines}）" >&2
      exit 1
    fi
  done < <(find cmd internal web/src -type f \( -name '*.go' -o -name '*.ts' -o -name '*.tsx' \) -print0)

  while IFS= read -r directory; do
    files="$(find "${directory}" -maxdepth 1 -type f | wc -l | tr -d ' ')"
    if (( files > 8 )); then
      echo "错误：目录直接文件超过 8 个：${directory}（${files}）" >&2
      exit 1
    fi
  done < <(find cmd internal scripts web/src -type d)

  unformatted="$(gofmt -l cmd internal)"
  if [[ -n "${unformatted}" ]]; then
    echo "错误：以下 Go 文件未格式化：" >&2
    echo "${unformatted}" >&2
    exit 1
  fi

  go vet ./...
  "${PROJECT_ROOT}/scripts/test.sh"
  "${PROJECT_ROOT}/scripts/build.sh"
} 2>&1 | tee "${LOG_DIR}/check.log"
