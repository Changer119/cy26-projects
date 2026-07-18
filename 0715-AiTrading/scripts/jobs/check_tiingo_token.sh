#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/common.sh"

ENV_FILE="${PROJECT_ROOT}/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "缺少 .env" >&2
  exit 1
fi

token="$(awk '/^TIINGO_API_KEY=/{print substr($0, index($0, "=") + 1)}' "${ENV_FILE}" | tail -1)"
token="${token%$'\r'}"
token="${token#\"}"
token="${token%\"}"
if [[ -z "${token}" ]]; then
  echo "TIINGO_API_KEY 为空" >&2
  exit 1
fi

response_file="$(mktemp)"
trap 'rm -f "${response_file}"' EXIT
status="$({
  printf 'Authorization: Token %s\n' "${token}" | \
  curl --silent --show-error --output "${response_file}" --write-out '%{http_code}' \
    --header @- \
    --get 'https://api.tiingo.com/tiingo/daily/603005/prices' \
    --data-urlencode 'startDate=2026-07-15' \
    --data-urlencode 'endDate=2026-07-15'
} 2>>"${PROJECT_ROOT}/logs/data-smoke.log")"

case "${status}" in
  200)
    if grep -Eq '^[[:space:]]*\[[[:space:]]*\][[:space:]]*$' "${response_file}"; then
      echo "Tiingo 鉴权成功，但目标日期无数据"
      exit 2
    fi
    echo "Tiingo 鉴权成功，603005 的目标日期数据可读"
    ;;
  401|403)
    echo "Tiingo 鉴权失败（HTTP ${status}）" >&2
    exit 1
    ;;
  *)
    echo "Tiingo 请求失败（HTTP ${status}）" >&2
    exit 1
    ;;
esac
