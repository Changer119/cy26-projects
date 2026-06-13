#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/update-readme.log"
README_FILE="${README_PATH:-$ROOT_DIR/../README.md}"
AUTO_START="<!-- AUTO_UPDATE_START -->"
AUTO_END="<!-- AUTO_UPDATE_END -->"

mkdir -p "$LOG_DIR"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

ensure_readme() {
  if [[ -f "$README_FILE" ]]; then
    return
  fi

  mkdir -p "$(dirname "$README_FILE")"
  {
    echo "# GitHub Action Demo"
    echo
    echo "$AUTO_START"
    echo "$AUTO_END"
  } > "$README_FILE"
}

ensure_markers() {
  if grep -qF "$AUTO_START" "$README_FILE" && grep -qF "$AUTO_END" "$README_FILE"; then
    return
  fi

  {
    echo
    echo "$AUTO_START"
    echo "$AUTO_END"
  } >> "$README_FILE"
}

update_readme() {
  local updated_at
  local block_file
  local temp_file
  local new_block

  updated_at="$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
  block_file="$(mktemp)"
  temp_file="$(mktemp)"
  new_block="$(cat <<MARKDOWN
- 最近更新时间：$updated_at
- 由 GitHub Actions 定时更新，也可以通过 \`workflow_dispatch\` 手动触发。
- 当前仓库：\`${GITHUB_REPOSITORY:-local/demo}\`
MARKDOWN
)"
  printf "%s\n" "$new_block" > "$block_file"

  awk -v start="$AUTO_START" -v end="$AUTO_END" -v block_file="$block_file" '
    $0 == start {
      print
      while ((getline line < block_file) > 0) {
        print line
      }
      close(block_file)
      skipping = 1
      next
    }
    $0 == end {
      skipping = 0
      print
      next
    }
    !skipping {
      print
    }
  ' "$README_FILE" > "$temp_file"

  mv "$temp_file" "$README_FILE"
  rm -f "$block_file"
  log "updated $README_FILE"
}

{
  log "start update README"
  ensure_readme
  ensure_markers
  update_readme
  log "README update finished"
} 2>&1 | tee "$LOG_FILE"
