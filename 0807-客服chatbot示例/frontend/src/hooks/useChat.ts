"use client";

import { useCallback, useState } from "react";
import type { ChatMessage } from "@/types/chat";
import { ChatApiError, sendChatMessage } from "@/lib/api";

function createMessage(
  role: ChatMessage["role"],
  content: string,
  sources?: string[],
): ChatMessage {
  return { id: crypto.randomUUID(), role, content, sources };
}

interface UseChatResult {
  messages: ChatMessage[];
  isSending: boolean;
  errorMessage: string | null;
  sendMessage: (text: string) => Promise<void>;
}

/**
 * 聊天会话状态管理。session_id 在页面加载时生成一次，
 * 后续所有请求复用同一个 session_id 以维持多轮上下文。
 */
export function useChat(sessionId: string): UseChatResult {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isSending) return;

      setErrorMessage(null);
      setMessages((prev) => [...prev, createMessage("user", trimmed)]);
      setIsSending(true);

      try {
        const response = await sendChatMessage({
          session_id: sessionId,
          message: trimmed,
        });
        setMessages((prev) => [
          ...prev,
          createMessage("assistant", response.reply, response.sources),
        ]);
      } catch (error) {
        const message =
          error instanceof ChatApiError
            ? error.message
            : "发生未知错误，请稍后重试";
        setErrorMessage(message);
      } finally {
        setIsSending(false);
      }
    },
    [isSending, sessionId],
  );

  return { messages, isSending, errorMessage, sendMessage };
}
