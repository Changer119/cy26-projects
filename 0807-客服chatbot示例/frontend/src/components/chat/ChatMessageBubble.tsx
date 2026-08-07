import type { ChatMessage } from "@/types/chat";

interface ChatMessageBubbleProps {
  message: ChatMessage;
}

/** 单条聊天气泡：区分用户/助手样式，助手消息附带知识库来源 */
export function ChatMessageBubble({ message }: ChatMessageBubbleProps) {
  const isUser = message.role === "user";
  const hasSources = !isUser && !!message.sources && message.sources.length > 0;

  return (
    <div className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-6 whitespace-pre-wrap break-words ${
          isUser
            ? "rounded-br-sm bg-blue-600 text-white"
            : "rounded-bl-sm bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
        }`}
      >
        <p>{message.content}</p>
        {hasSources && (
          <div className="mt-2 border-t border-zinc-300/50 pt-2 dark:border-zinc-600/50">
            <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
              参考来源
            </p>
            <ul className="mt-1 space-y-0.5">
              {message.sources?.map((source, index) => (
                <li
                  key={`${message.id}-source-${index}`}
                  className="text-xs text-zinc-500 dark:text-zinc-400"
                >
                  {source}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
