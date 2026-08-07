# 前端（内部客服 Chatbot 聊天界面）

负责范围：`frontend/` 目录，Next.js（App Router）+ React + TypeScript + Tailwind CSS 4。

## 目录结构

```
frontend/src/
├── app/
│   ├── layout.tsx              根布局，设置页面 metadata
│   ├── page.tsx                首页，渲染 ChatWindow
│   └── globals.css
├── components/chat/
│   ├── ChatWindow.tsx           聊天窗口容器，持有 session_id 与聊天状态
│   ├── ChatMessageList.tsx      消息列表，自动滚动到底部、发送中 loading 气泡
│   ├── ChatMessageBubble.tsx    单条消息气泡，助手消息展示 sources
│   ├── ChatInput.tsx            输入框 + 发送按钮，Enter 发送/Shift+Enter 换行
│   └── ChatErrorBanner.tsx      请求失败时的友好错误提示
├── hooks/
│   ├── useChat.ts                聊天消息状态与发送逻辑
│   └── useSessionId.ts           进入页面时生成一次 session_id（crypto.randomUUID）
├── lib/
│   └── api.ts                    封装 /api/chat、/api/health 调用，统一处理网络/HTTP/格式错误
└── types/
    └── chat.ts                   与后端契约对应的强类型定义（ChatRequest/ChatResponse/ChatMessage）
```

## 与后端的接口契约

来源：`discuss/技术方案.md`，前后端并行开发期间锁定，不修改字段。

```
POST /api/chat
Request:  { "session_id": string, "message": string }
Response: { "session_id": string, "reply": string, "sources": string[] }

GET /api/health
Response: { "status": "ok" }
```

后端地址通过环境变量 `NEXT_PUBLIC_API_BASE_URL` 配置，默认值 `http://localhost:8000`（见 `frontend/.env.example`）。本地开发如需覆盖，复制为 `frontend/.env.local` 后修改。

## 会话管理

- 打开页面时用 `crypto.randomUUID()` 生成一个 `session_id`（`useSessionId` hook），页面生命周期内保持不变。
- 每次发送消息都带上同一个 `session_id`，由后端维持多轮上下文。
- 页面刷新会重新生成 `session_id`，即开启新会话（MVP 阶段不做跨刷新的会话持久化）。

## 错误处理

`lib/api.ts` 中统一抛出 `ChatApiError`，覆盖三类失败场景：网络不可达（后端未启动）、HTTP 非 2xx 状态码、返回数据不符合契约结构。`useChat` hook 捕获后设置 `errorMessage`，由 `ChatErrorBanner` 展示为页面内的提示条，不会导致白屏或页面崩溃；用户已发送的消息仍保留在列表中，可以重新发送。

## 本地运行

统一通过项目根目录 `scripts/start-frontend.sh` / `scripts/stop-frontend.sh` 启停，不要直接执行 npm 命令：

```bash
./scripts/start-frontend.sh   # 首次运行会自动 npm install，随后启动 dev server（默认端口 3000）
./scripts/stop-frontend.sh    # 停止 dev server
```

- 日志输出到项目根目录 `logs/frontend.log`（进程日志）与 `logs/frontend-install.log`（依赖安装日志，仅首次）。
- 可通过环境变量 `FRONTEND_PORT` 覆盖默认端口。

## 已知限制

- 后端服务未启动或 `DEEPSEEK_API_KEY` 未配置时，发送消息会展示错误提示条（如"无法连接客服后端服务"或"后端服务返回错误"），这是并行开发阶段的预期行为，集成校验阶段两端联调后应恢复正常。
- 未做消息持久化，刷新页面会清空当前会话（含 `session_id`）。
- 未做鉴权/多用户区分，仅面向内部单人使用场景的 MVP 演示。
