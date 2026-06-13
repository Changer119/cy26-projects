# Loop Engineering CI/CD 演示

## 1. 什么是 Loop Engineering

传统的人机协作模式是"一次性"的：开发者提交代码 → CI 跑出失败结果 → 人去看日志 → 人来修复 → 再次提交。

Loop Engineering 强调的是把这个反馈环交给 Agent 自主驱动，形成一个持续运转的闭环：

```
感知 (Perceive)  →  运行 CI Gate，读取 lint / 测试结果
决策 (Decide)    →  分析失败原因，定位需要修改的代码
行动 (Act)       →  修复代码
验证 (Verify)    →  重新运行 CI Gate
   └──── 未通过则继续循环，直到全部通过 ────┘
```

Agent 不需要人在每一轮失败后介入，只需要在循环开始前设定好"目标状态"（本例中是 `scripts/ci.sh` 退出码为 0），循环会一直运行直到目标达成。

## 2. 本项目的场景

`src/loop_demo/` 是一个极简的"订单处理"模块：

- `pricing.py`：折扣 / 税费计算
- `inventory.py`：库存校验与预留

`tests/` 中是这两个模块对应的测试，代表"正确的业务预期"。

为了演示效果，`src/` 中的实现**故意埋入了几处 bug**：

1. `apply_discount`：折扣计算用加法而不是减法
2. `calculate_tax`：税费计算用减法而不是加法
3. `has_sufficient_stock`：库存恰好等于请求量时误判为不足（`>` 应为 `>=`）
4. `reserve_items`：使用了可变默认参数 `reserved=[]`，导致多次调用的预留记录互相串联
5. `inventory.py` 中存在一个未使用的 `import os`（lint 错误）

`scripts/ci.sh` 模拟了一条最小 CI 流水线：先跑 `ruff check`（lint），再跑 `pytest`（测试），两者都通过才算 CI 通过。`.github/workflows/ci.yml` 是同一套检查在真实 GitHub Actions 中的映射。

## 3. 第一步：复现 CI 失败（baseline）

```bash
bash scripts/setup.sh   # 安装依赖（uv sync）
bash scripts/ci.sh       # 运行 CI gate，预期失败
```

此时应该能看到：

- 1 个 lint 错误（未使用的 `import os`）
- 5 个测试失败（5 处业务逻辑 bug）

日志会写入 `logs/lint.log` 和 `logs/test.log`，这就是 Agent 在循环中要"感知"的输入。

## 4. 第二步：用 `/loop` 启动自愈循环

在 Claude Code 中，使用内置的 `/loop` 技能，让 Agent 自主驱动"运行 CI → 修复 → 再运行"的循环，直到 CI 全绿。可以让 Agent 自行决定每轮节奏（不传固定间隔）：

```
/loop 运行 bash scripts/ci.sh。如果失败，根据 logs/lint.log 和
logs/test.log 中的报错信息，定位 src/loop_demo/ 中的具体 bug 并修复
（每轮只修复定位最明确的一个问题，避免一次改太多）。修复后重新运行
bash scripts/ci.sh 验证。当 CI 全部通过（退出码为 0）时，结束循环。
```

每一轮循环大致会经历：

1. 运行 `scripts/ci.sh`，读取 lint / 测试结果
2. 选定一个失败项，定位对应代码
3. 修复代码
4. 重新运行 `scripts/ci.sh` 验证
5. 若仍有失败，进入下一轮；若全部通过，结束循环

## 5. 预期结果

循环结束时：

- `bash scripts/ci.sh` 退出码为 `0`
- `ruff check` 无报错
- 全部 6 个测试通过

整个过程中人不需要逐条分析报错或手动改代码，只需要在循环开始前定义清楚"目标状态"和"每轮可以做什么"。

## 6. 与传统 CI/CD 的对比

| | 传统模式 | Loop Engineering |
|---|---|---|
| 失败响应 | 人工查看日志、定位、修复 | Agent 自主感知 - 决策 - 行动 - 验证 |
| 迭代单位 | 一次 PR / 一次提交 | 一个循环 round，可在单次会话内完成多轮 |
| 人的角色 | 执行修复 | 定义目标状态与约束条件 |
| 终止条件 | 人判断"看起来好了" | 客观的可验证条件（CI gate 退出码） |

## 7. GitHub Actions 版自愈循环

前面两种方式都依赖本地 Claude Code 会话。`.github/workflows/self-heal.yml` 把同一个循环搬到了 CI 环境里：循环在**单次 Action job 内部**用 `scripts/self_heal_loop.sh` 完成，全程在 Actions 日志里可观察。

### 7.1 循环逻辑（`scripts/self_heal_loop.sh`）

```
for round in 1..5:
    运行 scripts/ci.sh
    若通过 → 结束循环
    否则 → 调用 claude -p "<修复一个bug>" --dangerously-skip-permissions
           本地 git commit（标记 [auto-fix N/5]）
若 5 轮后仍失败 → 再跑一次 ci.sh 确认最终状态，job 标记为失败
```

### 7.2 前置配置

1. 在 GitHub repo 的 `Settings → Secrets and variables → Actions` 中添加以下三个 secrets（通过兼容 Anthropic 协议的代理接入第三方模型，例如 DeepSeek）：
   - `ANTHROPIC_BASE_URL`：兼容 Anthropic API 协议的代理地址
   - `ANTHROPIC_AUTH_TOKEN`：代理使用的认证 token
   - `ANTHROPIC_MODEL`：实际使用的模型名
2. 确保存在 `loop-demo` 分支，且 `src/loop_demo/` 是带 5 处 bug 的 baseline 版本

### 7.3 触发方式

- **手动触发**：进入 GitHub 仓库的 Actions 页面，选择 "Self-Heal CI Loop" workflow，点击 "Run workflow"，选择 `loop-demo` 分支运行
- **push 触发**：向 `loop-demo` 分支 push 代码（例如重新埋入 bug 后 push），会自动触发该 workflow

### 7.4 观察循环过程

打开对应的 Action run，在 "运行自愈循环" 这一步的日志中可以看到：

- 每一轮 `scripts/ci.sh` 的输出（lint + 测试结果）
- 每一轮 Claude 修复时的思考与改动
- 每一轮结束后生成的 `[auto-fix N/5]` commit

循环结束（CI 通过或达到 5 轮上限）后，"推送修复结果" 步骤会把所有 commit 一次性 push 回 `loop-demo` 分支。

### 7.5 重置 demo

把 `src/loop_demo/pricing.py` 和 `src/loop_demo/inventory.py` 还原成带 5 处 bug 的版本，push 到 `loop-demo` 分支，即可重新触发一轮完整的自愈循环。
