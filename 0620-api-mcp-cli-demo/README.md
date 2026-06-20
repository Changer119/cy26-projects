# 天气查询 demo：一份能力，三种封装

演示如何把同一份「核心能力」分别封装成 **CLI / MCP / HTTP** 三种对外形态。
核心能力：输入城市 + 日期 → 调用 DeepSeek 大模型（OpenAI 兼容格式）→ 返回结构化天气信息。

## 架构

```
              ┌─────────────┐
   人/脚本 →  │   CLI 层    │ ─┐
              └─────────────┘  │
              ┌─────────────┐  │     ┌──────────────────────┐
   AI Agent → │   MCP 层    │ ─┼──→  │  core/service.py     │  ← 真正的业务逻辑
              └─────────────┘  │     │  （协议无关，单一真相源）│
              ┌─────────────┐  │     └──────────────────────┘
   程序     → │  HTTP API   │ ─┘
              └─────────────┘
```

判断架构是否正确的标准：**改一条业务规则，只动 `core/`，三个适配层一行都不用改。**

```
src/weather/
├── core/            # 协议无关的核心层
│   ├── models.py    # 强类型数据结构 WeatherQuery / WeatherResult
│   ├── service.py   # get_weather() —— 调用 DeepSeek（OpenAI 兼容），结构化输出
│   └── logger.py    # 统一日志（输出到 logs/）
└── adapters/        # 三个薄薄的翻译层
    ├── cli.py       # Typer
    ├── http.py      # FastAPI
    └── mcp.py       # FastMCP
```

## 快速开始

```bash
# 1. 安装依赖（uv），并生成 .env
scripts/setup.sh

# 2. 在 .env 中填入 DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL

# 3. 任选一种形态运行
scripts/run_cli.sh 杭州 2026-06-20            # CLI（人类可读）
scripts/run_cli.sh 杭州 2026-06-20 --json     # CLI（JSON，供脚本消费）
scripts/run_http.sh                           # HTTP，访问 /docs
scripts/run_mcp.sh                            # MCP（stdio）
```

## 三种封装的区别

| 维度 | CLI | MCP | HTTP |
|------|-----|-----|------|
| 使用者 | 人 / 脚本 | AI / Agent | 程序 / 服务 |
| 关键点 | 参数与可读输出 | 工具的自描述（description） | 网络协议与契约 |

> 注：本 demo 直接让大模型生成合理天气（适合演示封装架构）。若要真实天气，
> 可在 `core/service.py` 中接入真实天气 API，三个适配层无需改动。
>
> 大模型统一使用 DeepSeek（OpenAI 兼容格式），配置全部来自环境变量：
> `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL`。
