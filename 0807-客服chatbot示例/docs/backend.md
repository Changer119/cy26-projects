# 后端服务说明（backend/）

内部客服 chatbot 的后端，Python + FastAPI，用 `uv` 管理依赖与运行。

## 目录结构

```
backend/
├── main.py              # 服务入口，仅创建 app，实际启动走 scripts/start-backend.sh
├── pyproject.toml        # uv 项目配置
├── .env.example           # DeepSeek 配置占位示例
├── .env                   # 本地环境变量（不提交，需自行填写真实 key）
├── app/
│   ├── config.py          # 环境变量配置（Settings）
│   ├── logger.py          # 日志初始化，输出到 backend/logs/
│   ├── models.py          # 全部接口/内部数据模型（Pydantic 强类型）
│   ├── chat_service.py    # 对话编排：检索 + 拼上下文 + 调用 DeepSeek + 更新会话
│   ├── dependencies.py    # FastAPI 依赖注入（单例检索器/ChatService）
│   ├── server.py          # FastAPI 应用工厂
│   ├── api/                # 路由：/api/health、/api/chat
│   ├── rag/                # 知识库加载（loader.py）+ BM25 检索（retriever.py）
│   ├── llm/                # DeepSeek 调用封装（deepseek_client.py）
│   └── session/            # 进程内会话历史存储（store.py）
├── data/                   # 示例知识库文档（5 篇 Markdown）
├── logs/                   # 运行日志（backend.log 滚动文件 + uvicorn.out.log）
└── tests/                  # 单元测试（pytest，均 mock 掉 DeepSeek）
```

## 启动与停止

统一通过项目根 `scripts/` 目录下的脚本操作，不要直接敲 `uv run` / `python`：

```bash
./scripts/start-backend.sh   # 启动，默认监听 8000 端口
./scripts/stop-backend.sh    # 停止
```

启动脚本会自动 `uv sync` 同步依赖。停止脚本按命令行特征匹配整个进程树
（含 `uv run` fork 出的 uvicorn 子进程），避免残留孤儿进程占用端口。

验证服务是否正常：

```bash
curl http://localhost:8000/api/health
# {"status":"ok"}
```

## 配置 DeepSeek（必须，才能让 /api/chat 真正生成回复）

1. 复制 `backend/.env.example` 为 `backend/.env`。
2. 填写三项配置：
   - `DEEPSEEK_API_KEY`：DeepSeek 平台申请的 API Key
   - `DEEPSEEK_BASE_URL`：默认 `https://api.deepseek.com`
   - `DEEPSEEK_MODEL`：默认 `deepseek-chat`
3. 重启服务（`./scripts/stop-backend.sh && ./scripts/start-backend.sh`）。

**如果 `.env` 里 `DEEPSEEK_API_KEY` 为空或调用失败**：`/api/chat` 不会崩溃，
会返回 `502` 状态码 + 清晰的 `detail` 错误信息（例如
`DeepSeek 未配置：请在 backend/.env 中设置 DEEPSEEK_API_KEY`），
方便排查而不是进程异常退出。

## 接口契约（与前端锁定，禁止变更字段）

```
POST /api/chat
Request:  { "session_id": string, "message": string }
Response: { "session_id": string, "reply": string, "sources": string[] }

GET /api/health
Response: { "status": "ok" }
```

调用示例：

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-1","message":"年假怎么申请"}'
```

`sources` 字段返回命中的知识库文件名（如 `请假流程.md`），供前端展示引用来源；
未检索到相关内容时为空数组。

## RAG 检索实现

- 知识库文档放在 `backend/data/`，纯 Markdown，当前有 5 篇：
  `请假流程.md`、`报销流程.md`、`IT设备申请.md`、`差旅政策.md`、`入职引导.md`。
- 检索方案：本地 BM25（`rank-bm25`）+ `jieba` 中文分词，**不依赖任何外部
  embedding API**（DeepSeek 不提供 embedding 接口，这是关键词检索而非语义
  向量检索的直接原因）。
- 文档按空行分段后聚合成约 300 字的片段（chunk），每次对话检索 top-k
  （默认 3，`RAG_TOP_K` 环境变量可调，见 `app/config.py`）个最相关片段，
  拼进发给 DeepSeek 的 system prompt 上下文中。
- 新增/修改知识库文档：直接编辑或新增 `backend/data/*.md` 文件，服务重启后
  会重新构建索引（索引在进程启动时一次性加载，不支持热更新）。

## 会话管理

- `session_id` 由前端生成并在每次请求中携带，后端用进程内 `dict`（`app/session/store.py`）
  保存每个 session 的多轮历史，MVP 阶段不落库，服务重启后历史会丢失。
- 单个 session 最多保留最近 20 条消息（10 轮问答），超出后自动丢弃最早的记录，
  避免长会话导致内存无限增长（可通过 `SESSION_MAX_TURNS` 调整）。

## 单元测试

```bash
cd backend && uv run pytest -v
```

覆盖范围：
- `tests/test_rag_retriever.py`：文档加载、BM25 检索命中相关性、空知识库边界情况。
- `tests/test_chat_service.py`：对话编排逻辑（mock 检索器 + mock DeepSeek 客户端），
  验证多轮历史持久化、来源去重、DeepSeek 未配置/调用失败时的报错行为。
- `tests/test_api_chat.py`：FastAPI 接口层，验证 `/api/health`、`/api/chat`
  返回结构严格符合契约，以及参数校验、502 错误路径（均通过依赖注入 mock 掉
  `ChatService`，不发起真实网络请求）。

以上测试均不需要真实的 `DEEPSEEK_API_KEY` 即可运行。

## 已知限制

- 会话历史纯内存存储，服务重启即丢失，不适合生产环境多进程/多副本部署。
- 检索是关键词（BM25）而非语义向量检索，遇到同义词/改写表达可能召回不准，
  例如问题中的关键词和文档里的表述差异较大时命中率会下降。
- 知识库索引在进程启动时构建一次，运行时新增文档不会自动生效，需重启服务。
- 未做鉴权/限流，仅作为内部 demo 使用。
