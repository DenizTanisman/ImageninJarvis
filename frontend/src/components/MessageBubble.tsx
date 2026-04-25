import { cn } from "@/lib/utils";

export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  text: string;
  createdAt: number;
}

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  return (
    <div
      data-testid={`msg-${message.role}`}
      className={cn(
        "flex w-full",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      <div
        className={cn(
          "max-w-[75%] rounded-2xl px-4 py-2 text-sm leading-relaxed shadow",
          isUser
            ? "bg-sky-500/90 text-white"
            : "bg-slate-800/80 text-slate-100 ring-1 ring-slate-700",
        )}
      >
        {message.text}
      </div>
    </div>
  );
}
