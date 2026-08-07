"use client";

import { useChat } from "@/hooks/useChat";
import { useSessionId } from "@/hooks/useSessionId";
import { ChatErrorBanner } from "./ChatErrorBanner";
import { ChatInput } from "./ChatInput";
import { ChatMessageList } from "./ChatMessageList";

/** 聊天窗口容器：拼装消息列表、错误提示、输入框，持有本次会话的 session_id */
export function ChatWindow() {
  const sessionId = useSessionId();
  const { messages, isSending, errorMessage, sendMessage } = useChat(sessionId);

  return (
    <div className="flex h-full w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <header className="border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
        <h1 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">
          内部客服助手
        </h1>
        <p className="text-xs text-zinc-400">基于知识库检索回答内部问题</p>
      </header>

      <ChatMessageList messages={messages} isSending={isSending} />

      {errorMessage && <ChatErrorBanner message={errorMessage} />}

      <ChatInput onSend={sendMessage} disabled={isSending} />
    </div>
  );
}
