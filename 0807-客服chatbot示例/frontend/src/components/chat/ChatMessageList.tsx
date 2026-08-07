"use client";

import { useEffect, useRef } from "react";
import type { ChatMessage } from "@/types/chat";
import { ChatMessageBubble } from "./ChatMessageBubble";

interface ChatMessageListProps {
  messages: ChatMessage[];
  isSending: boolean;
}

/** 消息列表：自动滚动到底部，发送中时展示 loading 气泡 */
export function ChatMessageList({ messages, isSending }: ChatMessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 min-h-0 items-center justify-center px-6 text-center text-sm text-zinc-400">
        向内部客服助手提问，获取知识库检索结果
      </div>
    );
  }

  return (
    <div className="flex flex-1 min-h-0 flex-col gap-3 overflow-y-auto px-4 py-4">
      {messages.map((message) => (
        <ChatMessageBubble key={message.id} message={message} />
      ))}
      {isSending && (
        <div className="flex justify-start">
          <div className="rounded-2xl rounded-bl-sm bg-zinc-100 px-4 py-2.5 text-sm text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
            正在思考...
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
