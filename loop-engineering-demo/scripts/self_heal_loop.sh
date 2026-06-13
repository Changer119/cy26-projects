#!/usr/bin/env bash
# 自愈循环：反复运行 CI gate，失败则调用 Claude Code 修复一个 bug，
# 直到 CI 全部通过或达到最大轮数。
# 每修复一轮，会在本地创建一个 commit；push 由调用方负责。
set -uo pipefail
cd "$(dirname "$0")/.."

MAX_ROUNDS=5

FIX_PROMPT='运行 bash scripts/ci.sh 脚本，如果失败，根据 logs/lint.log 和
logs/test.log 中的报错信息，找到问题，修复 src/loop_demo 下的代码。
有多个错误时，只修改最有把握的一个 bug，避免一次改多个 bug 出现不可预测的结果。
修复后不需要自己再运行验证，也不需要 git commit，我会在你结束后自己验证和提交。'

for round in $(seq 1 "$MAX_ROUNDS"); do
    echo "==> Round $round/$MAX_ROUNDS: 运行 CI gate"
    if bash scripts/ci.sh; then
        echo "CI 通过，循环结束"
        exit 0
    fi

    echo "==> Round $round/$MAX_ROUNDS: CI 失败，调用 Claude Code 修复一个 bug"
    claude -p "$FIX_PROMPT" --dangerously-skip-permissions

    if [ -z "$(git status --porcelain)" ]; then
        echo "本轮 Claude 未修改任何文件，停止循环"
        exit 1
    fi

    git add -A
    git commit -m "[auto-fix $round/$MAX_ROUNDS] 自愈循环自动修复"
done

echo "==> 已达最大轮数 ($MAX_ROUNDS)，再次运行 CI gate 确认最终状态"
bash scripts/ci.sh
