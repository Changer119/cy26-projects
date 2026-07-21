#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TEMP_DIR}"' EXIT
PORT="${PHONE2COMPUTER_PORT:-18765}"

CONFIG_JSON="$(curl --silent --show-error --fail "http://127.0.0.1:${PORT}/api/admin/config")"
UPLOAD_URL="$(printf '%s' "${CONFIG_JSON}" | jq -r '.upload_url')"
TOKEN="${UPLOAD_URL##*token=}"
CONTENT="phone2computer-smoke"
FILENAME="$(printf 'smoke-test.jpg' | base64)"
MODIFIED="$(printf '1700000000000' | base64)"

curl --silent --show-error --fail \
  --dump-header "${TEMP_DIR}/create.headers" \
  --output /dev/null \
  --request POST \
  --header "Authorization: Bearer ${TOKEN}" \
  --header "Tus-Resumable: 1.0.0" \
  --header "Upload-Length: ${#CONTENT}" \
  --header "Upload-Metadata: filename ${FILENAME},lastmodified ${MODIFIED}" \
  "http://127.0.0.1:${PORT}/api/files/"

LOCATION="$(awk 'tolower($1) == "location:" { gsub("\r", "", $2); print $2 }' "${TEMP_DIR}/create.headers")"
if [[ -z "${LOCATION}" ]]; then
  echo "冒烟测试失败：未返回上传地址" >&2
  exit 1
fi

curl --silent --show-error --fail \
  --output /dev/null \
  --request PATCH \
  --header "Authorization: Bearer ${TOKEN}" \
  --header "Tus-Resumable: 1.0.0" \
  --header "Upload-Offset: 0" \
  --header "Content-Type: application/offset+octet-stream" \
  --data-binary "${CONTENT}" \
  "http://127.0.0.1:${PORT}${LOCATION}"

OFFSET="$(curl --silent --show-error --fail --head \
  --header "Authorization: Bearer ${TOKEN}" \
  --header "Tus-Resumable: 1.0.0" \
  "http://127.0.0.1:${PORT}${LOCATION}" | awk 'tolower($1) == "upload-offset:" { gsub("\r", "", $2); print $2 }')"

if [[ "${OFFSET}" != "${#CONTENT}" ]]; then
  echo "冒烟测试失败：服务端偏移量 ${OFFSET} 与内容长度 ${#CONTENT} 不一致" >&2
  exit 1
fi

echo "端到端冒烟测试通过：创建、上传、落盘和偏移查询均正常。"
