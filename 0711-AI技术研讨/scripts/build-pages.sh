#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SLIDES_FILE="$ROOT_DIR/slides/ai-team-transformation.html"
DOCUMENT_FILE="$ROOT_DIR/docs/ai-team-transformation.md"
OUTPUT_DIR="$ROOT_DIR/dist/pages"
PRESENTATION_DIR="$OUTPUT_DIR/ai-team-transformation"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/build-pages.log"

mkdir -p "$LOG_DIR"

{
  printf '[%s] 构建 GitHub Pages 发布目录\n' "$(date '+%Y-%m-%d %H:%M:%S')"

  for source_file in "$SLIDES_FILE" "$DOCUMENT_FILE"; do
    if [[ ! -f "$source_file" ]]; then
      printf '缺少发布源文件：%s\n' "$source_file" >&2
      exit 1
    fi
  done

  rm -rf "$OUTPUT_DIR"
  mkdir -p "$PRESENTATION_DIR"

  cp "$SLIDES_FILE" "$PRESENTATION_DIR/index.html"
  cp "$DOCUMENT_FILE" "$PRESENTATION_DIR/ai-team-transformation.md"
  touch "$OUTPUT_DIR/.nojekyll"

  printf '%s\n' \
    '<!doctype html>' \
    '<html lang="zh-CN">' \
    '<head>' \
    '  <meta charset="utf-8">' \
    '  <meta name="viewport" content="width=device-width, initial-scale=1">' \
    '  <meta http-equiv="refresh" content="0; url=./ai-team-transformation/">' \
    '  <title>AI 技术团队转型</title>' \
    '</head>' \
    '<body>' \
    '  <p><a href="./ai-team-transformation/">进入 AI 技术团队转型演示</a></p>' \
    '</body>' \
    '</html>' >"$OUTPUT_DIR/index.html"

  printf '发布入口：%s\n' "$OUTPUT_DIR/index.html"
  printf '演示入口：%s\n' "$PRESENTATION_DIR/index.html"
  printf '[%s] GitHub Pages 发布目录构建完成\n' "$(date '+%Y-%m-%d %H:%M:%S')"
} 2>&1 | tee -a "$LOG_FILE"
