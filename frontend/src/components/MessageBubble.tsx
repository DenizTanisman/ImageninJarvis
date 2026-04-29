import ReactMarkdown from "react-markdown";

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

// Render assistant messages as markdown so headings, lists, and paragraph
// breaks from capabilities (Journal report, etc.) come through visually
// instead of as raw "###" / "**" text. User messages stay plain.
const MARKDOWN_COMPONENTS = {
  h1: (props: any) => (
    <h1 className="mb-2 mt-3 text-base font-bold text-slate-50" {...props} />
  ),
  h2: (props: any) => (
    <h2 className="mb-2 mt-3 text-sm font-bold text-slate-50" {...props} />
  ),
  h3: (props: any) => (
    <h3
      className="mb-1.5 mt-2.5 text-sm font-semibold text-slate-100"
      {...props}
    />
  ),
  p: (props: any) => <p className="mb-2 last:mb-0" {...props} />,
  ul: (props: any) => (
    <ul className="mb-2 list-disc space-y-1 pl-5" {...props} />
  ),
  ol: (props: any) => (
    <ol className="mb-2 list-decimal space-y-1 pl-5" {...props} />
  ),
  li: (props: any) => <li {...props} />,
  strong: (props: any) => (
    <strong className="font-semibold text-slate-50" {...props} />
  ),
  em: (props: any) => <em className="italic text-slate-200" {...props} />,
  code: (props: any) => (
    <code
      className="rounded bg-slate-900/60 px-1 py-0.5 font-mono text-xs"
      {...props}
    />
  ),
  a: (props: any) => (
    <a
      className="text-sky-300 underline hover:text-sky-200"
      target="_blank"
      rel="noreferrer"
      {...props}
    />
  ),
};

function AssistantMarkdown({ text }: { text: string }) {
  return (
    <div className="text-sm leading-relaxed text-slate-100">
      <ReactMarkdown components={MARKDOWN_COMPONENTS}>{text}</ReactMarkdown>
    </div>
  );
}

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
          <div className="mb-2">
            <AssistantMarkdown text={message.text} />
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
          "rounded-2xl px-4 py-2 shadow",
          isUser
            ? "max-w-[75%] bg-sky-500/90 text-sm leading-relaxed text-white"
            : "max-w-[85%] bg-slate-800/80 ring-1 ring-slate-700",
        )}
      >
        {isUser ? message.text : <AssistantMarkdown text={message.text} />}
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
