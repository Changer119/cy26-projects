#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="${ROOT_DIR}/wechat-karpathy-ppt-video"
LOG_FILE="${ROOT_DIR}/logs/wechat_karpathy_assets.log"

mkdir -p "${ROOT_DIR}/logs" "${PROJECT_DIR}/assets"
cd "${ROOT_DIR}"

{
  echo "[wechat-karpathy-assets] $(date '+%Y-%m-%d %H:%M:%S')"
  uv run python - <<'PY'
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

extract = json.loads(Path("outputs/wechat-ppt-video/article_extract.json").read_text(encoding="utf-8"))
selected = {
    "article-cover.jpg": extract["images"][0]["src"],
    "karpathy-quote.png": extract["images"][2]["src"],
    "agent-demo.png": extract["images"][5]["src"],
    "frontier-note.png": extract["images"][14]["src"],
}
headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://mp.weixin.qq.com/"}
asset_dir = Path("wechat-karpathy-ppt-video/assets")
for name, url in selected.items():
    request = urllib.request.Request(url, headers=headers)
    target = asset_dir / name
    with urllib.request.urlopen(request, timeout=30) as response:
        target.write_bytes(response.read())
    print(f"saved {target} {target.stat().st_size} bytes")
PY
} 2>&1 | tee "${LOG_FILE}"
