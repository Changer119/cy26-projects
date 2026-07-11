#!/bin/bash
# xgx_common.sh —— 学习新干线自动挂课 · 公共库（被其他脚本 source，不单独运行）
#
# 提供：
#   - 配置与日志（Logger with File Output → logs/）
#   - CDP Proxy 封装：eval / targets / screenshot / clickxy / navigate / close
#   - 业务原子操作：定位 learn 页、等待列表就绪、读课程清单与进度、
#                   打开某门课的播放页(open_course)、启动播放(start_play, iframe 中心法)
#
# 复用 fc-study-xgx-skill 的脚本：click_xy.mjs / check_playing.sh
# 所有浏览器操作经本地 CDP Proxy（直连用户日常 Chrome，天然携带登录态）。

# ---------------------------------------------------------------------------
# 配置（均可用环境变量覆盖）
# ---------------------------------------------------------------------------
export PROXY="${PROXY:-http://localhost:3456}"
XGX_BASE_URL="${XGX_BASE_URL:-https://learning.hzrs.hangzhou.gov.cn}"
XGX_LEARN_URL="${XGX_LEARN_URL:-$XGX_BASE_URL/#/learn}"
XGX_SKILL_DIR="${XGX_SKILL_DIR:-$HOME/.claude/skills/fc-study-xgx-skill/scripts}"
XGX_WEBACCESS_DEPS="${XGX_WEBACCESS_DEPS:-$HOME/.claude/skills/web-access/scripts/check-deps.mjs}"

# 目录（基于本脚本所在位置推导，cron / 任意 CWD 调用都正确）
XGX_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
XGX_PROJECT_DIR="$(cd "$XGX_SCRIPT_DIR/.." && pwd)"
XGX_LOG_DIR="${XGX_LOG_DIR:-$XGX_PROJECT_DIR/logs}"
XGX_DATA_DIR="${XGX_DATA_DIR:-$XGX_PROJECT_DIR/data}"
mkdir -p "$XGX_LOG_DIR" "$XGX_DATA_DIR"

# 日志文件（调用方可在 source 后覆盖 XGX_LOG）
XGX_LOG="${XGX_LOG:-$XGX_LOG_DIR/xgx_$(date '+%Y%m%d').log}"

# ---------------------------------------------------------------------------
# 日志：输出到 stderr + 文件，绝不污染函数 stdout（函数返回值靠 stdout）
# ---------------------------------------------------------------------------
xgx_log()  { printf '%s [INFO ] %s\n' "$(date '+%F %T')" "$*" | tee -a "$XGX_LOG" >&2; }
xgx_warn() { printf '%s [WARN ] %s\n' "$(date '+%F %T')" "$*" | tee -a "$XGX_LOG" >&2; }
xgx_err()  { printf '%s [ERROR] %s\n' "$(date '+%F %T')" "$*" | tee -a "$XGX_LOG" >&2; }

# ---------------------------------------------------------------------------
# Proxy 基础
# ---------------------------------------------------------------------------

# proxy 是否存活
xgx_proxy_alive() { curl -s -m 5 "$PROXY/targets" >/dev/null 2>&1; }

# 确保 proxy 可用；未启动则尝试用 web-access 的 check-deps 拉起
xgx_proxy_ensure() {
  if xgx_proxy_alive; then return 0; fi
  xgx_warn "CDP Proxy 未响应，尝试启动 ($XGX_WEBACCESS_DEPS) ..."
  if [ -f "$XGX_WEBACCESS_DEPS" ]; then
    node "$XGX_WEBACCESS_DEPS" >>"$XGX_LOG" 2>&1 || true
  fi
  local i
  for i in $(seq 1 10); do
    xgx_proxy_alive && { xgx_log "CDP Proxy 就绪"; return 0; }
    sleep 1
  done
  xgx_err "CDP Proxy 启动失败：请确认 Chrome 已开启远程调试（chrome://inspect/#remote-debugging）"
  return 1
}

# POST /eval，返回 JS 表达式的 value（纯文本）。偶发空/串台 → 自动重试一次。
xgx_eval() {
  local target="$1" js="$2" out
  local attempt
  for attempt in 1 2; do
    out=$(curl -s -m 20 -X POST "$PROXY/eval?target=$target" --data "$js" 2>/dev/null \
      | python3 -c 'import sys,json
try:
    d=json.load(sys.stdin); sys.stdout.write(str(d.get("value","")))
except Exception:
    pass')
    [ -n "$out" ] && { printf '%s' "$out"; return 0; }
    sleep 1
  done
  printf '%s' "$out"   # 可能为空字符串
  return 0
}

# 把任意字符串安全编码为 JS 字面量（带引号，保留中文），用于嵌入 eval 的 JS
xgx_js_str() { python3 -c 'import sys,json;print(json.dumps(sys.argv[1],ensure_ascii=False))' "$1"; }

# GET /targets 原始 JSON
xgx_targets_json() { curl -s -m 10 "$PROXY/targets" 2>/dev/null; }

# 当前所有 tab 的 targetId（空格分隔）
xgx_target_ids() {
  xgx_targets_json | python3 -c 'import sys,json
try:
    print(" ".join(t["targetId"] for t in json.load(sys.stdin)))
except Exception:
    pass'
}

# 找第一个 url 含 <substr> 的 tab，返回 targetId（无则空）
xgx_find_tab_by_url() {
  local substr="$1"
  xgx_targets_json | SUB="$substr" python3 -c 'import sys,json,os
sub=os.environ["SUB"]
try:
    for t in json.load(sys.stdin):
        if sub in t.get("url",""):
            print(t["targetId"]); break
except Exception:
    pass'
}

# 取某 tab 的 url
xgx_tab_url() {
  curl -s -m 10 "$PROXY/info?target=$1" 2>/dev/null | python3 -c 'import sys,json
try:
    print(json.load(sys.stdin).get("url",""))
except Exception:
    pass'
}

# 新建后台 tab，返回 targetId
xgx_new_tab() {
  curl -s -m 15 "$PROXY/new?url=$1" 2>/dev/null | python3 -c 'import sys,json
try:
    print(json.load(sys.stdin).get("targetId",""))
except Exception:
    pass'
}

xgx_navigate() { curl -s -m 15 "$PROXY/navigate?target=$1&url=$2" >/dev/null 2>&1; }
xgx_close_tab() { curl -s -m 10 "$PROXY/close?target=$1" >/dev/null 2>&1; }

# 等待出现「不在 before 集合、且 url 含 substr」的新 tab，返回其 targetId
# 用法: xgx_wait_new_tab "<before ids 空格分隔>" "<url substr>" [timeout_s]
xgx_wait_new_tab() {
  local before="$1" substr="$2" timeout="${3:-14}" i tid
  for i in $(seq 1 "$timeout"); do
    tid=$(xgx_targets_json | BEFORE="$before" SUB="$substr" python3 -c 'import sys,json,os
before=set(os.environ["BEFORE"].split()); sub=os.environ["SUB"]
try:
    for t in json.load(sys.stdin):
        if t["targetId"] not in before and sub in t.get("url",""):
            print(t["targetId"]); break
except Exception:
    pass')
    [ -n "$tid" ] && { printf '%s' "$tid"; return 0; }
    sleep 1
  done
  return 1
}

# ---------------------------------------------------------------------------
# 复用 skill 脚本
# ---------------------------------------------------------------------------
xgx_clickxy() { node "$XGX_SKILL_DIR/click_xy.mjs" --x "$2" --y "$3" --target "$1" >/dev/null 2>&1; }
xgx_check_playing() { PROXY="$PROXY" bash "$XGX_SKILL_DIR/check_playing.sh" "$1" 2>/dev/null; }

# ---------------------------------------------------------------------------
# 学习页：定位 / 就绪 / 刷新
# ---------------------------------------------------------------------------

# 找到 #/learn tab；没有则新建。返回 targetId
xgx_learn_tab() {
  local tid
  tid=$(xgx_find_tab_by_url "#/learn")
  if [ -z "$tid" ]; then
    tid=$(xgx_new_tab "$XGX_LEARN_URL")
    sleep 2
  fi
  printf '%s' "$tid"
}

# 等列表数据加载完（出现「开始学习」）。就绪返回 0
xgx_learn_ready() {
  local learn="$1" i r
  for i in $(seq 1 8); do
    r=$(xgx_eval "$learn" 'document.body.innerText.includes("开始学习")?"READY":"WAIT"')
    [ "$r" = "READY" ] && return 0
    sleep 2
  done
  return 1
}

# 刷新学习页（让进度列更新），并等就绪
xgx_learn_refresh() {
  local learn="$1"
  xgx_eval "$learn" 'location.reload();"ok"' >/dev/null
  sleep 3
  xgx_learn_ready "$learn"
}

# 检查是否未登录（url 跳到登录页）。是→返回 0
xgx_is_logged_out() {
  local url; url=$(xgx_tab_url "$1")
  case "$url" in
    *user.zjzwfw.gov.cn/pc/login*|*"#/login"*) return 0 ;;
    *) return 1 ;;
  esac
}

# ---------------------------------------------------------------------------
# 课程清单 / 进度（基于「学习」按钮的顺序索引，不依赖按钮文案、不依赖课名特殊字符）
# ---------------------------------------------------------------------------

# 列出前若干门课：每行 "进度%\t课程名"，按列表顺序。
# 依据：所有文本含「学习」的按钮(开始/继续/重新学习)即各门课入口，顺序=课程顺序。
xgx_list_courses() {
  local learn="$1"
  xgx_eval "$learn" '(()=>{const bs=[...document.querySelectorAll("button,a")].filter(x=>/学习/.test(x.textContent)&&!/删除/.test(x.textContent));const out=bs.map(b=>{let c=b;for(let i=0;i<6;i++){c=c.parentElement;if(c&&c.textContent.length>20)break;}const t=c?c.innerText.replace(/\s+/g," ").trim():"";const m=t.match(/(\d+)%/);const pct=m?m[1]:"0";const name=t.replace(/^\s*/,"").replace(/\s*(专业课程|一般公需|公需课程|必修|选修).*$/,"").trim();return pct+"\t"+name;});return out.join("\n");})()'
}

# 按课名定位它当前在「学习按钮序列」中的索引(1起)，找不到返回 0。
# 用于纠正「某门完成后按钮文案变化/消失导致的 index 漂移」。
xgx_index_of_name() {
  local learn="$1" lit; lit=$(xgx_js_str "$2")
  xgx_eval "$learn" "(()=>{const name=$lit;const bs=[...document.querySelectorAll('button,a')].filter(x=>/学习/.test(x.textContent)&&!/删除/.test(x.textContent));for(let i=0;i<bs.length;i++){let c=bs[i];for(let j=0;j<6;j++){c=c.parentElement;if(c&&c.textContent.length>20)break;}if(c&&c.innerText.includes(name))return String(i+1);}return '0';})()"
}

# 读第 idx(从1起) 门课的进度整数（0-100）。读不到返回空
xgx_course_progress() {
  local learn="$1" idx="$2"
  xgx_eval "$learn" "(()=>{const bs=[...document.querySelectorAll('button,a')].filter(x=>/学习/.test(x.textContent)&&!/删除/.test(x.textContent));const b=bs[$idx-1];if(!b)return'';let c=b;for(let i=0;i<6;i++){c=c.parentElement;if(c&&c.textContent.length>20)break;}const m=(c?c.innerText:'').match(/(\\d+)%/);return m?m[1]:'0';})()"
}

# ---------------------------------------------------------------------------
# 打开某门课的播放页：点第 idx 个「学习」按钮 → 详情页「立即学习」 → 播放页
# 成功输出播放页 targetId（stdout），失败返回非 0
# ---------------------------------------------------------------------------
xgx_open_course() {
  local learn="$1" idx="$2" before detail play r

  before=$(xgx_target_ids)
  r=$(xgx_eval "$learn" "(()=>{const bs=[...document.querySelectorAll('button,a')].filter(x=>/学习/.test(x.textContent)&&!/删除/.test(x.textContent));const b=bs[$idx-1];if(!b)return'no-btn';b.click();return'clicked';})()")
  [ "$r" = "clicked" ] || { xgx_err "点击第 $idx 个学习按钮失败: $r"; return 1; }

  detail=$(xgx_wait_new_tab "$before" "CourseDetail" 12) || { xgx_err "未打开课程详情页"; return 1; }

  # 等详情页「立即学习」出现再点
  local i ready=""
  for i in $(seq 1 6); do
    [ "$(xgx_eval "$detail" 'document.body.innerText.includes("立即学习")?"Y":"N"')" = "Y" ] && { ready=1; break; }
    sleep 2
  done
  [ -n "$ready" ] || { xgx_err "详情页无「立即学习」按钮"; xgx_close_tab "$detail"; return 1; }

  xgx_eval "$detail" "(()=>{const b=[...document.querySelectorAll('button,a')].find(x=>x.textContent.includes('立即学习'));if(!b)return'no';b.click();return'clicked';})()" >/dev/null

  play=$(xgx_wait_new_tab "$before" "#/class?courseId=" 14) || { xgx_err "未打开播放页"; xgx_close_tab "$detail"; return 1; }

  xgx_close_tab "$detail"          # 详情页用完即关，保持干净
  printf '%s' "$play"
  return 0
}

# ---------------------------------------------------------------------------
# 启动播放：iframe 中心法（无需视觉、无需 dpr 换算）
#   播放器内容是跨域 iframe，读不到内部；但 iframe 元素的 getBoundingClientRect
#   在父页面可读 → 算出几个候选点（画面中心 / 左下控制条▶ / 再点中心），
#   每点一次用 check_playing 验证，PLAYING 即成功。
# 成功返回 0
# ---------------------------------------------------------------------------
xgx_start_play() {
  local play="$1" rect i state
  local retry="${XGX_PLAY_RETRY:-6}"
  local l t w h vw vh

  for i in $(seq 1 "$retry"); do
    # 读 iframe 矩形：l,t,w,h（CSS 像素）
    rect=$(xgx_eval "$play" '(()=>{const f=document.querySelector("iframe");if(!f)return"";const r=f.getBoundingClientRect();return Math.round(r.left)+","+Math.round(r.top)+","+Math.round(r.width)+","+Math.round(r.height);})()')

    local cx cy
    if [ -n "$rect" ]; then
      IFS=',' read -r l t w h <<<"$rect"
      case "$((i % 3))" in
        1) cx=$(( l + w/2 ));  cy=$(( t + h/2 )) ;;            # 画面中心（大播放器=▶）
        2) cx=$(( l + 20 ));   cy=$(( t + h*92/100 )) ;;       # 左下控制条 ▶（小窗布局）
        0) cx=$(( l + w/2 ));  cy=$(( t + h*45/100 )) ;;       # 中上（部分布局▶偏上）
      esac
    else
      # 拿不到 iframe，退回视口比例兜底
      local vp; vp=$(xgx_eval "$play" 'window.innerWidth+","+window.innerHeight')
      IFS=',' read -r vw vh <<<"${vp:-960,912}"
      cx=$(( vw/2 )); cy=$(( vh*47/100 ))
    fi

    xgx_log "尝试启动播放 #$i 点击 ($cx,$cy)"
    xgx_clickxy "$play" "$cx" "$cy"
    state=$(xgx_check_playing "$play")
    [ "$state" = "PLAYING" ] && { xgx_log "已开始播放"; return 0; }
    sleep 2
  done

  xgx_err "$retry 次尝试后仍未播放（PAUSED）"
  return 1
}
