import { CalendarEventCard } from "@/components/capability/CalendarEventCard";
import { EventList } from "@/components/capability/EventList";
import { MailCard } from "@/components/capability/MailCard";
import { MailDraftCard } from "@/components/capability/MailDraftCard";
import { cn } from "@/lib/utils";
import type {
  CalendarEventDTO,
  MailDraftCardData,
  MailSummaryData,
} from "@/api/client";

export type MessageRole = "user" | "assistant";

export interface ChatMessagePayload {
  ui_type: string;
  data: unknown;
  meta?: Record<string, unknown>;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  text: string;
  createdAt: number;
  payload?: ChatMessagePayload;
}

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const richNode = !isUser ? renderPayload(message.payload) : null;

  if (richNode) {
    return (
      <div
        data-testid={`msg-${message.role}`}
        className="flex w-full justify-start"
      >
        <div className="w-full max-w-[90%] rounded-2xl bg-slate-800/80 p-3 shadow ring-1 ring-slate-700">
          <div className="mb-2 text-sm leading-relaxed text-slate-100">
            {message.text}
          </div>
          {richNode}
        </div>
      </div>
    );
  }

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

function renderPayload(payload: ChatMessagePayload | undefined) {
  if (!payload) return null;
  if (payload.ui_type === "MailCard" && isMailSummary(payload.data)) {
    return <MailCard initialData={payload.data} hideRangeSelector />;
  }
  if (payload.ui_type === "CalendarEvent" && isCalendarEvent(payload.data)) {
    const action = pickCalendarAction(payload.meta);
    return <CalendarEventCard event={payload.data} action={action} />;
  }
  if (payload.ui_type === "EventList" && isEventListData(payload.data)) {
    const isCandidates = payload.meta?.action === "delete_candidates";
    const headline = isCandidates
      ? "Birden fazla eşleşme buldum — silmek istediğine Sil de."
      : undefined;
    return (
      <EventList initialEvents={payload.data.events} headline={headline} />
    );
  }
  if (payload.ui_type === "MailDraftCard" && isMailDraft(payload.data)) {
    return <MailDraftCard data={payload.data} />;
  }
  return null;
}

function isMailDraft(value: unknown): value is MailDraftCardData {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.to === "string" &&
    typeof v.subject === "string" &&
    typeof v.body === "string"
  );
}

function isEventListData(
  value: unknown,
): value is { events: CalendarEventDTO[] } {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return Array.isArray(v.events) && v.events.every(isCalendarEvent);
}

function isMailSummary(value: unknown): value is MailSummaryData {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.categories === "object" &&
    v.categories !== null &&
    typeof v.total === "number" &&
    typeof v.needs_reply_count === "number"
  );
}

function isCalendarEvent(value: unknown): value is CalendarEventDTO {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.id === "string" &&
    typeof v.summary === "string" &&
    typeof v.start === "string" &&
    typeof v.end === "string"
  );
}

function pickCalendarAction(
  meta: Record<string, unknown> | undefined,
): "create" | "update" | "delete_proposal" {
  const a = meta?.action;
  if (a === "update" || a === "delete_proposal") return a;
  return "create";
}
