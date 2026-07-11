#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="${ROOT_DIR}/ideal-glasses-hyperframes"
INPUT_DIR="${ROOT_DIR}/inputs/理想AI眼镜"
OUTPUT_FILE="${ROOT_DIR}/outputs/理想AI眼镜-HyperFrames开盒入盒-5s.mp4"
LOG_FILE="${ROOT_DIR}/logs/ideal_glasses_hyperframes.log"
COMMAND="${1:-all}"

mkdir -p "${ROOT_DIR}/logs" "${ROOT_DIR}/outputs" "${PROJECT_DIR}/assets"

prepare_assets() {
  cd "${ROOT_DIR}"
  uv run auto-video-hyperframes-assets \
    --input-dir "${INPUT_DIR}" \
    --output-dir "${PROJECT_DIR}/assets"
}

run_lint() {
  cd "${PROJECT_DIR}"
  npx --yes hyperframes@0.6.110 lint --verbose
}

run_validate() {
  cd "${PROJECT_DIR}"
  npx --yes hyperframes@0.6.110 validate
}

run_inspect() {
  cd "${PROJECT_DIR}"
  npx --yes hyperframes@0.6.110 inspect --samples 12
}

run_render() {
  cd "${PROJECT_DIR}"
  npx --yes hyperframes@0.6.110 render --output "${OUTPUT_FILE}" --fps 30 --quality high
}

run_verify() {
  ffprobe -v error \
    -show_entries stream=codec_type,codec_name,width,height,r_frame_rate,duration \
    -show_entries format=duration,size \
    -of json "${OUTPUT_FILE}"
  for second in 0.8 2.4 4.4; do
    frame_name="${second/./_}"
    ffmpeg -y -ss "${second}" -i "${OUTPUT_FILE}" -frames:v 1 -update 1 \
      "${ROOT_DIR}/outputs/理想AI眼镜-hyperframes-frame-${frame_name}.jpg"
  done
}

{
  echo "[ideal-glasses-hyperframes] $(date '+%Y-%m-%d %H:%M:%S') ${COMMAND}"
  case "${COMMAND}" in
    prepare)
      prepare_assets
      ;;
    lint)
      prepare_assets
      run_lint
      ;;
    validate)
      prepare_assets
      run_validate
      ;;
    inspect)
      prepare_assets
      run_inspect
      ;;
    render)
      prepare_assets
      run_render
      ;;
    verify)
      run_verify
      ;;
    all)
      prepare_assets
      run_lint
      run_validate
      run_inspect
      run_render
      run_verify
      ;;
    *)
      echo "用法：$0 {prepare|lint|validate|inspect|render|verify|all}" >&2
      exit 2
      ;;
  esac
} 2>&1 | tee "${LOG_FILE}"
