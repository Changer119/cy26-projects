#!/bin/bash
# xgx_auto_study.sh —— 学习新干线 · 串行自动挂课
#
# 取「我的网络课程」前 N 门课，串行学习：学完一门(进度100%)自动学下一门，直到全部完成。
# 清单与进度写入 data/courses.md（人可读、可中断后查看），日志写入 logs/。
#
# 用法:
#   scripts/xgx_auto_study.sh [N]
#     N: 要学习的课程数量；缺省/0 表示「列表中全部课程」
#
# 环境变量（可选）:
#   XGX_POLL_INTERVAL  进度轮询间隔秒（默认 30）
#   XGX_MAX_MINUTES    单门课最长等待分钟（默认 90，超时跳过并标记 timeout）
#   PROXY              CDP Proxy 地址（默认 http://localhost:3456）
#
# 依赖: node, curl, python3, 以及 fc-study-xgx-skill 的 click_xy.mjs / check_playing.sh
set -uo pipefail

XGX_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=xgx_common.sh
source "$XGX_SCRIPT_DIR/xgx_common.sh"

# 本次运行日志单独成文件
XGX_LOG="$XGX_LOG_DIR/xgx_auto_$(date '+%Y%m%d_%H%M%S').log"
XGX_MD="$XGX_DATA_DIR/courses.md"
POLL_INTERVAL="${XGX_POLL_INTERVAL:-30}"
MAX_MINUTES="${XGX_MAX_MINUTES:-90}"

WANT_N="${1:-0}"

# --------------------------------------------------------------------------
# courses.md 读写。行格式（严格，便于解析）:
#   - [ ] 1 | 人工智能在智能制造中的应用（三） | 0%
#   状态符: [ ]=待学  [>]=学习中  [x]=已完成  [!]=超时跳过
# --------------------------------------------------------------------------

md_init() {
  # $1=总数  之后每行一个课名（按顺序）
  local total="$1"; shift
  {
    echo "# 学习新干线 · 挂课清单"
    echo
    echo "> 模式：串行自动（学完一门自动学下一门）"
    echo "> 生成时间：$(date '+%F %T')"
    echo "> 状态：\`[ ]\`待学  \`[>]\`学习中  \`[x]\`已完成  \`[!]\`超时跳过"
    echo
    local i=1 name
    for name in "$@"; do
      printf -- "- [ ] %d | %s | 0%%\n" "$i" "$name"
      i=$((i+1))
    done
  } > "$XGX_MD"
  xgx_log "清单已写入 $XGX_MD（共 $total 门）"
}

# 更新第 idx 门课的状态符与进度。 $1=idx $2=mark(空格/>/x/!) $3=pct(可空,保持原值)
md_update() {
  local idx="$1" mark="$2" pct="${3:-}"
  IDX="$idx" MARK="$mark" PCT="$pct" python3 - "$XGX_MD" <<'PY'
import sys,os,re
path=sys.argv[1]; idx=int(os.environ["IDX"]); mark=os.environ["MARK"]; pct=os.environ["PCT"]
lines=open(path,encoding="utf-8").read().splitlines()
pat=re.compile(r'^- \[.\] (\d+) \| (.*) \| (\d+)%\s*$')
for k,l in enumerate(lines):
    m=pat.match(l)
    if m and int(m.group(1))==idx:
        name=m.group(2); p=pct if pct!="" else m.group(3)
        lines[k]=f"- [{mark}] {idx} | {name} | {p}%"
        break
open(path,"w",encoding="utf-8").write("\n".join(lines)+"\n")
PY
}

# --------------------------------------------------------------------------
# 学习单门课：打开播放页 → 启动播放 → 轮询进度直到 100% 或超时
#   $1=learn  $2=row(清单固定序号,用于 md)  $3=课程名
#   返回 0=完成  1=超时/失败
# --------------------------------------------------------------------------
study_one() {
  local learn="$1" row="$2" name="$3" play pct state didx
  xgx_log "▶ 开始第 $row 门：$name"
  md_update "$row" ">"

  # DOM 按钮序号(didx)：按课名校正，避免前面课程完成后按钮变化导致的 index 漂移。
  # 注意 didx 仅用于页面 DOM 操作；md 始终用清单固定序号 row。
  didx="$row"
  local r; r=$(xgx_index_of_name "$learn" "$name")
  if [ -n "$r" ] && [ "$r" -gt 0 ] 2>/dev/null && [ "$r" -ne "$row" ]; then
    xgx_warn "索引漂移：第 $row 门按课名实际位于第 $r 个学习按钮，DOM 操作已校正"
    didx="$r"
  fi

  play=$(xgx_open_course "$learn" "$didx") || { xgx_warn "打开播放页失败，跳过第 $row 门"; md_update "$row" "!"; return 1; }
  xgx_log "播放页 tab=$play"

  if ! xgx_start_play "$play"; then
    xgx_warn "无法自动启动播放，跳过第 $row 门（可人工点开 $play 后重跑）"
    md_update "$row" "!"
    xgx_close_tab "$play"
    return 1
  fi

  local deadline=$(( $(date +%s) + MAX_MINUTES*60 ))
  while :; do
    sleep "$POLL_INTERVAL"

    # 保活：播放页若被暂停则重新启动
    state=$(xgx_check_playing "$play")
    if [ "$state" = "PAUSED" ]; then
      xgx_warn "检测到暂停，重新启动播放"
      xgx_start_play "$play" || true
    fi

    # 刷新学习页读取最新进度（按课名重新定位 DOM 序号，刷新后顺序仍可能变）
    if xgx_learn_refresh "$learn"; then
      r=$(xgx_index_of_name "$learn" "$name")
      [ -n "$r" ] && [ "$r" -gt 0 ] 2>/dev/null && didx="$r"
      pct=$(xgx_course_progress "$learn" "$didx")
      [ -n "$pct" ] || pct=0
      xgx_log "进度 第$row门：${pct}%"
      md_update "$row" ">" "$pct"
      if [ "$pct" -ge 100 ] 2>/dev/null; then
        xgx_log "✔ 完成第 $row 门：$name"
        md_update "$row" "x" "100"
        xgx_close_tab "$play"
        return 0
      fi
    else
      xgx_warn "学习页刷新失败，稍后重试"
    fi

    if [ "$(date +%s)" -ge "$deadline" ]; then
      xgx_warn "第 $row 门超过 ${MAX_MINUTES} 分钟仍未完成，跳过"
      md_update "$row" "!" "$pct"
      xgx_close_tab "$play"
      return 1
    fi
  done
}

# --------------------------------------------------------------------------
main() {
  xgx_log "=== 学习新干线 自动挂课启动（目标: ${WANT_N} 门，0=全部）==="
  xgx_proxy_ensure || exit 1

  local learn; learn=$(xgx_learn_tab)
  [ -n "$learn" ] || { xgx_err "无法获取学习页 tab"; exit 1; }
  xgx_log "学习页 tab=$learn"

  if xgx_is_logged_out "$learn"; then
    xgx_err "当前未登录学习新干线。请在 Chrome 中登录 $XGX_BASE_URL 后重跑本脚本。"
    exit 2
  fi

  xgx_learn_ready "$learn" || { xgx_err "学习页列表未加载出「开始学习」，请确认已登录且有课程"; exit 1; }

  # 读课程清单（进度\t课名）
  local listing; listing=$(xgx_list_courses "$learn")
  [ -n "$listing" ] || { xgx_err "未读到任何课程"; exit 1; }

  # 解析课名数组
  local names=() pcts=()
  while IFS=$'\t' read -r pct name; do
    [ -n "$name" ] || continue
    pcts+=("$pct"); names+=("$name")
  done <<< "$listing"

  local total="${#names[@]}"
  local target="$WANT_N"
  if [ "$target" -le 0 ] 2>/dev/null || [ "$target" -gt "$total" ]; then target="$total"; fi
  xgx_log "列表共 $total 门，本次学习前 $target 门"

  md_init "$target" "${names[@]:0:$target}"

  # 串行学习
  local i done_cnt=0 skip_cnt=0
  for i in $(seq 1 "$target"); do
    local nm="${names[$((i-1))]}" cur
    # 已是 100% 则直接标记完成
    cur="${pcts[$((i-1))]}"
    if [ "$cur" -ge 100 ] 2>/dev/null; then
      xgx_log "第 $i 门已完成（${cur}%），跳过：$nm"
      md_update "$i" "x" "100"; done_cnt=$((done_cnt+1)); continue
    fi
    if study_one "$learn" "$i" "$nm"; then
      done_cnt=$((done_cnt+1))
    else
      skip_cnt=$((skip_cnt+1))
    fi
  done

  xgx_log "=== 全部结束：完成 $done_cnt 门，跳过 $skip_cnt 门。清单见 $XGX_MD ==="
}

main "$@"
