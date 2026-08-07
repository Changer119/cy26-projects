/**
 * 与后端 /api/chat、/api/health 契约对应的强类型定义。
 * 契约来源：0807-客服chatbot示例/discuss/技术方案.md，前后端并行开发期间保持锁定，不要修改字段。
 */

export interface ChatRequest {
  session_id: string;
  message: string;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  sources: string[];
}

export interface HealthResponse {
  status: string;
}

/** 消息发送方角色 */
export type MessageRole = "user" | "assistant";

/** 渲染在聊天窗口里的一条消息（前端内部状态，不直接对应接口契约） */
export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  /** 仅助手消息可能携带命中的知识库片段来源 */
  sources?: string[];
}
