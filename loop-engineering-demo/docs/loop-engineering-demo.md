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
