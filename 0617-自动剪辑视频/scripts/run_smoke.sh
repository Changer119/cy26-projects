#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs
LOG_FILE="logs/smoke.log"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] smoke"
  mkdir -p outputs/smoke outputs/analysis
  ffmpeg -y -f lavfi -i testsrc2=duration=6:size=1280x720:rate=30 -pix_fmt yuv420p outputs/smoke/source.mp4
  cat > outputs/analysis/transcript.json <<'JSON'
{
  "segments": [
    {"start": 0.0, "end": 2.0, "text": "关键结论：先生成剪辑计划 JSON"},
    {"start": 2.0, "end": 3.0, "text": "嗯嗯就是这个那个"},
    {"start": 3.0, "end": 6.0, "text": "第二步按计划导出竖屏字幕视频"}
  ]
}
JSON
  cat > outputs/analysis/silences.json <<'JSON'
[
  {"start": 2.0, "end": 3.0}
]
JSON
  uv run auto-video-edit plan --input outputs/smoke/source.mp4 --max-duration 5 --silence-threshold 0.8
  uv run auto-video-edit edit --plan outputs/plan.json
  ffprobe -v error -show_entries format=duration -of default=nk=1:nw=1 outputs/final.mp4
} 2>&1 | tee "$LOG_FILE"
