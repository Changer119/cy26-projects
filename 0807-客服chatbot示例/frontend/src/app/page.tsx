import { ChatWindow } from "@/components/chat/ChatWindow";

export default function Home() {
  return (
    <div className="flex flex-1 items-center justify-center bg-zinc-50 p-4 dark:bg-black">
      <ChatWindow />
    </div>
  );
}
