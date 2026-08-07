#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="${ROOT_DIR}/air-circulator-family-ad"
ASSET_DIR="${PROJECT_DIR}/assets"
FAMILY_DIR="${ASSET_DIR}/images/family"
PRODUCT_DIR="${ASSET_DIR}/images/product"
LOG_FILE="${ROOT_DIR}/logs/air_circulator_family_assets.log"

WIDE_SOURCE="${HOME}/.codex/generated_images/019f6100-ef92-7b10-8544-5c0878f7d275/exec-949411e0-3424-4eec-872c-ad9d3a18ddb7.png"
CLOSE_SOURCE="${HOME}/.codex/generated_images/019f6100-ef92-7b10-8544-5c0878f7d275/exec-0b20f20f-7602-4b3a-a450-eb761efad148.png"
PRODUCT_SOURCE="${HOME}/Downloads/空调扇aaa.png"
GSAP_SOURCE="${ROOT_DIR}/wechat-karpathy-ppt-video/assets/gsap.min.js"
FANGSONG_SOURCE="/System/Library/AssetsV2/com_apple_MobileAsset_Font7/1821952872c81043711aab6910052b65da8edf2c.asset/AssetData/STFANGSO.ttf"
ARIAL_UNICODE_SOURCE="/System/Library/Fonts/Supplemental/Arial Unicode.ttf"

mkdir -p "${ROOT_DIR}/logs" "${FAMILY_DIR}" "${PRODUCT_DIR}" "${ASSET_DIR}/audio" \
  "${ASSET_DIR}/fonts" "${ASSET_DIR}/vendor" "${ASSET_DIR}/previews"

{
  echo "[air-circulator-family-assets] $(date '+%Y-%m-%d %H:%M:%S')"

  for source in "${WIDE_SOURCE}" "${CLOSE_SOURCE}" "${PRODUCT_SOURCE}" \
    "${GSAP_SOURCE}" "${FANGSONG_SOURCE}" "${ARIAL_UNICODE_SOURCE}"; do
    if [ ! -f "${source}" ]; then
      echo "missing asset source: ${source}" >&2
      exit 1
    fi
  done

  rm -f "${ASSET_DIR}/images/family-wide.png" "${ASSET_DIR}/images/family-close.png" \
    "${ASSET_DIR}/images/product-source.png" "${ASSET_DIR}/images/product-cutout.png"

  cp "${WIDE_SOURCE}" "${FAMILY_DIR}/wide.png"
  cp "${WIDE_SOURCE}" "${FAMILY_DIR}/closing.png"
  cp "${CLOSE_SOURCE}" "${FAMILY_DIR}/close.png"
  cp "${PRODUCT_SOURCE}" "${PRODUCT_DIR}/source.png"
  cp "${GSAP_SOURCE}" "${ASSET_DIR}/vendor/gsap.min.js"
  cp "${FANGSONG_SOURCE}" "${ASSET_DIR}/fonts/STFANGSO.ttf"
  cp "${ARIAL_UNICODE_SOURCE}" "${ASSET_DIR}/fonts/ArialUnicode.ttf"

  ffmpeg -y -hide_banner -loglevel error \
    -i "${PRODUCT_DIR}/source.png" \
    -vf "crop=500:1260:195:20,format=rgba,colorkey=0x525354:0.12:0.035" \
    -frames:v 1 "${PRODUCT_DIR}/cutout.png"

  cp "${PRODUCT_DIR}/cutout.png" "${PRODUCT_DIR}/scene-1.png"
  cp "${PRODUCT_DIR}/cutout.png" "${PRODUCT_DIR}/scene-2.png"
  cp "${PRODUCT_DIR}/cutout.png" "${PRODUCT_DIR}/scene-3.png"
  cp "${PRODUCT_DIR}/cutout.png" "${PRODUCT_DIR}/scene-4.png"

  PAD_EXPR='0.012*(sin(2*PI*130.81*t)+0.72*sin(2*PI*164.81*t)+0.55*sin(2*PI*196*t)+0.34*sin(2*PI*246.94*t))*(0.84+0.16*sin(2*PI*0.10*t))'
  CHIME_EXPR='0.040*gte(t\,0.65)*exp(-2.4*(t-0.65))*sin(2*PI*523.25*(t-0.65))+0.032*gte(t\,3.35)*exp(-7.5*(t-3.35))*sin(2*PI*659.25*(t-3.35))+0.042*gte(t\,6.20)*exp(-2.5*(t-6.20))*sin(2*PI*587.33*(t-6.20))+0.042*gte(t\,10.25)*exp(-2.5*(t-10.25))*sin(2*PI*698.46*(t-10.25))+0.036*gte(t\,13.10)*exp(-2.3*(t-13.10))*sin(2*PI*783.99*(t-13.10))'

  ffmpeg -y -hide_banner -loglevel error \
    -f lavfi -i "aevalsrc=${PAD_EXPR}:s=48000:d=15" \
    -f lavfi -i "aevalsrc=${CHIME_EXPR}:s=48000:d=15" \
    -f lavfi -i "anoisesrc=color=pink:amplitude=0.006:duration=15:sample_rate=48000" \
    -filter_complex "[0:a]lowpass=f=1500,aecho=0.8:0.22:180|360:0.12|0.07,afade=t=in:st=0:d=1.2,afade=t=out:st=13.4:d=1.6[pad];[1:a]aecho=0.8:0.30:120|240:0.16|0.08[chime];[2:a]highpass=f=160,lowpass=f=1800,volume=0.28,afade=t=in:st=0:d=1.4,afade=t=out:st=13.2:d=1.8[air];[pad][chime][air]amix=inputs=3:normalize=0,pan=stereo|c0=c0|c1=c0,volume=12,alimiter=limit=0.70[mix]" \
    -map "[mix]" -c:a pcm_s16le "${ASSET_DIR}/audio/family-ad-bed.wav"

  ffmpeg -y -hide_banner -loglevel error \
    -i "${FAMILY_DIR}/wide.png" \
    -i "${PRODUCT_DIR}/cutout.png" \
    -filter_complex "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[bg];[1:v]scale=-1:900[product];[bg][product]overlay=x=W-w-38:y=H-h-72:format=auto" \
    -frames:v 1 "${ASSET_DIR}/previews/product-cutout-check.png"

  ffprobe -v error -select_streams v:0 \
    -show_entries stream=width,height,pix_fmt \
    -of default=noprint_wrappers=1 "${PRODUCT_DIR}/cutout.png"
  ffprobe -v error -select_streams a:0 \
    -show_entries stream=codec_name,sample_rate,channels:format=duration \
    -of default=noprint_wrappers=1 "${ASSET_DIR}/audio/family-ad-bed.wav"
  ffmpeg -hide_banner -loglevel info -i "${ASSET_DIR}/audio/family-ad-bed.wav" \
    -af volumedetect -f null - 2>&1 | sed -n '/mean_volume/p;/max_volume/p'
} 2>&1 | tee "${LOG_FILE}"
