"use client";

import { useState } from "react";

/**
 * 进入页面时生成一次 session_id，整个会话生命周期内保持不变，
 * 与后端约定的多轮对话上下文通过该 id 关联。
 */
export function useSessionId(): string {
  const [sessionId] = useState(() => crypto.randomUUID());
  return sessionId;
}
