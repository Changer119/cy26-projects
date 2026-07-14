#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SLIDES_FILE="$ROOT_DIR/slides/ai-team-transformation.html"
QA_DIR="$ROOT_DIR/logs/slide-qa"
LOG_FILE="$ROOT_DIR/logs/frontend-slides.log"
SESSION="ai-team-slides-qa"
URL="file://$SLIDES_FILE"

mkdir -p "$QA_DIR"
rm -rf "$QA_DIR/desktop" "$QA_DIR/laptop" "$QA_DIR/phone-portrait" "$QA_DIR/phone-landscape"
mkdir -p "$QA_DIR/desktop" "$QA_DIR/laptop" "$QA_DIR/phone-portrait" "$QA_DIR/phone-landscape"

cleanup() {
  agent-browser --session "$SESSION" close >>"$LOG_FILE" 2>&1 || true
}
trap cleanup EXIT

run_browser() {
  agent-browser --session "$SESSION" "$@"
}

capture_deck() {
  local width="$1"
  local height="$2"
  local output_dir="$3"
  local wait_ms="$4"

  run_browser set viewport "$width" "$height" >>"$LOG_FILE"
  run_browser press Home >>"$LOG_FILE"
  run_browser wait "$wait_ms" >>"$LOG_FILE"

  for index in $(seq 1 16); do
    printf -v filename 'slide-%02d.png' "$index"
    run_browser screenshot "$output_dir/$filename" >>"$LOG_FILE"
    if [[ "$index" -lt 16 ]]; then
      run_browser press ArrowRight >>"$LOG_FILE"
      run_browser wait "$wait_ms" >>"$LOG_FILE"
    fi
  done
}

{
  printf '[%s] 开始 Frontend Slides 验收\n' "$(date '+%Y-%m-%d %H:%M:%S')"
  printf '文件：%s\n' "$SLIDES_FILE"

  run_browser close >/dev/null 2>&1 || true
  run_browser --allow-file-access open "$URL"
  run_browser set viewport 1920 1080
  run_browser wait 1200

  printf '\n[DOM 与溢出检查]\n'
  run_browser eval --stdin <<'EVALEOF'
(async () => {
  await document.fonts.ready;
  const issues = [];
  const stage = document.querySelector('#deckStage');
  const slides = Array.from(document.querySelectorAll('.slide'));
  const active = slides.filter((slide) => slide.classList.contains('active') && slide.classList.contains('visible'));

  if (!stage) issues.push('缺少 #deckStage');
  if (slides.length !== 16) issues.push('幻灯片数量不是 16');
  if (active.length !== 1) issues.push('当前可见幻灯片数量不是 1');
  if (stage && (stage.clientWidth !== 1920 || stage.clientHeight !== 1080)) issues.push('固定画布不是 1920×1080');

  slides.forEach((slide, slideIndex) => {
    if (slide.clientWidth !== 1920 || slide.clientHeight !== 1080) {
      issues.push('第 ' + (slideIndex + 1) + ' 页尺寸异常');
    }
    const main = slide.querySelector('.slide-main');
    if (main && (main.scrollWidth > main.clientWidth + 1 || main.scrollHeight > main.clientHeight + 1)) {
      issues.push('第 ' + (slideIndex + 1) + ' 页主内容溢出');
    }
    const slideRect = slide.getBoundingClientRect();
    slide.querySelectorAll('[data-editable]').forEach((element, elementIndex) => {
      const rect = element.getBoundingClientRect();
      if (
        rect.left < slideRect.left - 1 ||
        rect.top < slideRect.top - 1 ||
        rect.right > slideRect.right + 1 ||
        rect.bottom > slideRect.bottom + 1
      ) {
        issues.push('第 ' + (slideIndex + 1) + ' 页文本 ' + (elementIndex + 1) + ' 越界');
      }
      const fontSize = Number.parseFloat(getComputedStyle(element).fontSize);
      if (fontSize < 15) {
        issues.push('第 ' + (slideIndex + 1) + ' 页文本 ' + (elementIndex + 1) + ' 字号低于 15px');
      }
    });
  });

  return JSON.stringify({
    passed: issues.length === 0,
    slideCount: slides.length,
    activeCount: active.length,
    editableCount: document.querySelectorAll('[data-editable]').length,
    stage: stage ? [stage.clientWidth, stage.clientHeight] : null,
    issues
  }, null, 2);
})()
EVALEOF

  printf '\n[键盘导航检查]\n'
  run_browser press End
  run_browser eval 'document.querySelectorAll(".slide.active.visible").length + ":" + document.getElementById("progressCounter").textContent'
  run_browser press Home
  run_browser press ArrowRight
  run_browser eval 'document.querySelectorAll(".slide.active.visible").length + ":" + document.getElementById("progressCounter").textContent'

  printf '\n[浏览器内编辑检查]\n'
  run_browser press e
  run_browser eval 'document.querySelectorAll("[contenteditable=true]").length'
  run_browser press e
  run_browser eval 'document.querySelectorAll("[contenteditable=true]").length'

  printf '\n[控制台错误检查]\n'
  run_browser errors

  printf '\n[截图：1920×1080]\n'
  capture_deck 1920 1080 "$QA_DIR/desktop" 560
  printf '[截图：1280×720]\n'
  capture_deck 1280 720 "$QA_DIR/laptop" 180
  printf '[截图：390×844]\n'
  capture_deck 390 844 "$QA_DIR/phone-portrait" 120
  printf '[截图：844×390]\n'
  capture_deck 844 390 "$QA_DIR/phone-landscape" 120

  printf '\n[固定舞台缩放检查]\n'
  run_browser eval --stdin <<'EVALEOF'
(() => {
  const stage = document.querySelector('#deckStage').getBoundingClientRect();
  return JSON.stringify({
    viewport: [window.innerWidth, window.innerHeight],
    stage: [Math.round(stage.width), Math.round(stage.height)],
    centered: Math.abs(stage.left - (window.innerWidth - stage.width) / 2) < 1 &&
      Math.abs(stage.top - (window.innerHeight - stage.height) / 2) < 1,
    ratio: Number((stage.width / stage.height).toFixed(4))
  });
})()
EVALEOF

  printf '\n[生成接触图]\n'
  ffmpeg -hide_banner -loglevel error -y -pattern_type glob -i "$QA_DIR/desktop/slide-*.png" \
    -vf "scale=480:270,tile=4x4" -frames:v 1 "$QA_DIR/contact-desktop.png"
  ffmpeg -hide_banner -loglevel error -y -pattern_type glob -i "$QA_DIR/laptop/slide-*.png" \
    -vf "scale=320:180,tile=4x4" -frames:v 1 "$QA_DIR/contact-laptop.png"
  ffmpeg -hide_banner -loglevel error -y -pattern_type glob -i "$QA_DIR/phone-portrait/slide-*.png" \
    -vf "scale=195:422,tile=4x4" -frames:v 1 "$QA_DIR/contact-phone-portrait.png"
  ffmpeg -hide_banner -loglevel error -y -pattern_type glob -i "$QA_DIR/phone-landscape/slide-*.png" \
    -vf "scale=422:195,tile=4x4" -frames:v 1 "$QA_DIR/contact-phone-landscape.png"

  printf '验收截图与接触图：%s\n' "$QA_DIR"
  printf '[%s] Frontend Slides 验收完成\n' "$(date '+%Y-%m-%d %H:%M:%S')"
} 2>&1 | tee -a "$LOG_FILE"
