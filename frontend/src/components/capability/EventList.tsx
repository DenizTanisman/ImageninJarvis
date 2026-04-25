import { CalendarDays, Clock } from "lucide-react";

import { MOCK_EVENTS } from "@/lib/mock-data";

export function EventList() {
  return (
    <ul data-testid="event-list" className="space-y-2">
      {MOCK_EVENTS.map((event) => (
        <li
          key={event.id}
          data-testid={`event-${event.id}`}
          className="rounded-xl border border-slate-800 bg-slate-900/50 p-3"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold text-slate-100">
                {event.title}
              </div>
              <div className="line-clamp-2 text-xs text-slate-400">
                {event.detail}
              </div>
            </div>
            <div className="shrink-0 space-y-1 text-right text-xs text-slate-400">
              <div className="flex items-center justify-end gap-1">
                <CalendarDays className="h-3 w-3" />
                {event.date}
              </div>
              <div className="flex items-center justify-end gap-1">
                <Clock className="h-3 w-3" />
                {event.time}
              </div>
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}
