#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/deploy-slides.log"
REPOSITORY="Changer119/cy26-projects"
WORKFLOW="pages-ai-team.yml"
BRANCH="main"
MODE="${1:-status}"

mkdir -p "$LOG_DIR"

if ! command -v gh >/dev/null 2>&1; then
  printf '未找到 GitHub CLI（gh）。\n' | tee -a "$LOG_FILE" >&2
  exit 1
fi

case "$MODE" in
  check)
    {
      printf '[%s] 检查 GitHub Pages 发布环境\n' "$(date '+%Y-%m-%d %H:%M:%S')"
      gh auth status
      gh repo view "$REPOSITORY" --json nameWithOwner,url,visibility,defaultBranchRef
      gh workflow view "$WORKFLOW" --repo "$REPOSITORY"
    } 2>&1 | tee -a "$LOG_FILE"
    ;;
  deploy)
    {
      printf '[%s] 手动触发 GitHub Pages 发布\n' "$(date '+%Y-%m-%d %H:%M:%S')"
      gh workflow run "$WORKFLOW" --repo "$REPOSITORY" --ref "$BRANCH"
      printf '已触发工作流，请运行：bash scripts/deploy-slides.sh watch\n'
    } 2>&1 | tee -a "$LOG_FILE"
    ;;
  status)
    {
      printf '[%s] 查询 GitHub Pages 发布状态\n' "$(date '+%Y-%m-%d %H:%M:%S')"
      gh run list --repo "$REPOSITORY" --workflow "$WORKFLOW" --limit 5
    } 2>&1 | tee -a "$LOG_FILE"
    ;;
  watch)
    {
      printf '[%s] 等待最近一次 GitHub Pages 发布完成\n' "$(date '+%Y-%m-%d %H:%M:%S')"
      RUN_ID="$(gh run list --repo "$REPOSITORY" --workflow "$WORKFLOW" --limit 1 --json databaseId --jq '.[0].databaseId')"
      if [[ -z "$RUN_ID" ]]; then
        printf '尚未找到 GitHub Pages 工作流记录。\n' >&2
        exit 1
      fi
      gh run watch "$RUN_ID" --repo "$REPOSITORY" --exit-status
    } 2>&1 | tee -a "$LOG_FILE"
    ;;
  *)
    printf '用法：bash scripts/deploy-slides.sh [check|deploy|status|watch]\n' >&2
    exit 1
    ;;
esac
