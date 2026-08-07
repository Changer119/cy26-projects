interface ChatErrorBannerProps {
  message: string;
}

/** 请求失败时的友好提示条，不让页面白屏崩溃 */
export function ChatErrorBanner({ message }: ChatErrorBannerProps) {
  return (
    <div className="mx-4 mb-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600 dark:bg-red-950/40 dark:text-red-400">
      {message}
    </div>
  );
}
