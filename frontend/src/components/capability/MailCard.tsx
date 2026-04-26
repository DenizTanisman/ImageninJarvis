import { Inbox, Loader2, Mail, Megaphone, MessagesSquare } from "lucide-react";
import { useEffect, useState } from "react";
import type { ComponentType, SVGProps } from "react";

import {
  ChatNetworkError,
  fetchMailSummary,
  getAuthStatus,
  googleConnectUrl,
  type AuthStatus,
  type MailEntry,
  type MailSummaryData,
} from "@/api/client";
import { BatchReplyView } from "@/components/capability/BatchReplyView";
import { MailRangeSelector } from "@/components/capability/MailRangeSelector";
import { cn } from "@/lib/utils";
import { MAIL_CATEGORY_COLOR, MAIL_CATEGORY_LABEL, type MailCategoryKey } from "@/lib/mock-data";
import { resolveRangeBounds, useMailUI } from "@/store/mail";

const CATEGORY_ICON: Record<MailCategoryKey, ComponentType<SVGProps<SVGSVGElement>>> = {
  important: Mail,
  dm: MessagesSquare,
  promo: Megaphone,
  other: Inbox,
};

const ORDER: MailCategoryKey[] = ["important", "dm", "promo", "other"];

interface MailCardProps {
  onReplyClick?: () => void;
}

function MailRow({ entry }: { entry: MailEntry }) {
  return (
    <li className="rounded-md border border-slate-800 bg-slate-900/50 px-3 py-2 text-sm">
      <div className="flex items-baseline justify-between gap-2">
        <span className="truncate font-medium text-slate-100">{entry.from}</span>
        {entry.needs_reply && (
          <span className="shrink-0 rounded-full bg-rose-500/20 px-2 py-0.5 text-[10px] uppercase text-rose-200">
            yanıt bekliyor
          </span>
        )}
      </div>
      <div className="truncate text-xs text-slate-300">{entry.subject}</div>
      <div className="line-clamp-2 text-xs text-slate-500">
        {entry.summary || entry.snippet}
      </div>
    </li>
  );
}

type LoadState =
  | { kind: "idle" }
  | { kind: "loading" }
  | {
      kind: "ready";
      data: MailSummaryData;
      authStatus: AuthStatus;
      cached: boolean;
    }
  | { kind: "error"; message: string }
  | { kind: "needs-auth" };

type ViewMode = "list" | "reply";

export function MailCard({ onReplyClick }: MailCardProps) {
  const range = useMailUI((s) => s.range);
  const [state, setState] = useState<LoadState>({ kind: "idle" });
  const [view, setView] = useState<ViewMode>("list");

  // Re-fetch whenever the range changes (kind switch or custom date edit).
  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    async function load() {
      setState({ kind: "loading" });
      setView("list");
      try {
        const status = await getAuthStatus(controller.signal);
        if (cancelled) return;
        if (!status.connected) {
          setState({ kind: "needs-auth" });
          return;
        }
        const bounds = resolveRangeBounds(range);
        const result = await fetchMailSummary(
          { range_kind: range.kind, ...bounds, max_results: 30 },
          controller.signal,
        );
        if (cancelled) return;
        if (result.ok) {
          setState({
            kind: "ready",
            data: result.data,
            authStatus: status,
            cached: result.meta?.source === "cache",
          });
        } else {
          setState({ kind: "error", message: result.error.user_message });
        }
      } catch (err) {
        if (cancelled) return;
        const message =
          err instanceof ChatNetworkError ? err.message : "Beklenmeyen bir hata.";
        setState({ kind: "error", message });
      }
    }

    void load();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [range]);

  const handleReplyClick = () => {
    onReplyClick?.();
    setView("reply");
  };

  return (
    <div data-testid="mail-card" className="space-y-4">
      {view === "list" && <MailRangeSelector />}
      <Body
        state={state}
        view={view}
        onReplyClick={handleReplyClick}
        onBackToList={() => setView("list")}
      />
    </div>
  );
}

function Body({
  state,
  view,
  onReplyClick,
  onBackToList,
}: {
  state: LoadState;
  view: ViewMode;
  onReplyClick: () => void;
  onBackToList: () => void;
}) {
  if (state.kind === "loading") {
    return (
      <div
        data-testid="mail-loading"
        className="flex items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-8 text-sm text-slate-400"
      >
        <Loader2 className="h-4 w-4 animate-spin text-sky-300" />
        Mailler getiriliyor…
      </div>
    );
  }

  if (state.kind === "needs-auth") {
    return (
      <div
        data-testid="mail-needs-auth"
        className="space-y-3 rounded-xl border border-amber-400/40 bg-amber-500/10 p-4 text-sm text-amber-100"
      >
        <p>Mail özetini çekebilmem için Google hesabını bağlamam gerek.</p>
        <a
          href={googleConnectUrl()}
          target="_blank"
          rel="noopener noreferrer"
          data-testid="connect-google"
          className="inline-flex items-center gap-2 rounded-lg bg-sky-500 px-3 py-2 text-xs font-semibold text-white transition hover:bg-sky-400"
        >
          Google'a bağlan
        </a>
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <div
        data-testid="mail-error"
        className="rounded-xl border border-rose-400/40 bg-rose-500/10 p-4 text-sm text-rose-100"
      >
        {state.message}
      </div>
    );
  }

  if (state.kind !== "ready") {
    return null;
  }

  const { data, authStatus, cached } = state;

  if (view === "reply") {
    return (
      <BatchReplyView
        summary={data}
        authStatus={authStatus}
        onClose={onBackToList}
      />
    );
  }

  return (
    <>
      {cached && (
        <p className="text-[10px] uppercase tracking-widest text-slate-500">
          Önbellekten — son 24 saat içinde alındı
        </p>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        {ORDER.map((key) => {
          const items = data.categories[key] ?? [];
          const Icon = CATEGORY_ICON[key];
          const extra = Math.max(0, items.length - 5);
          return (
            <section
              key={key}
              data-testid={`mail-cat-${key}`}
              className={cn(
                "space-y-2 rounded-xl border border-slate-800 bg-slate-950/50 p-3 ring-1",
                MAIL_CATEGORY_COLOR[key],
              )}
            >
              <header className="flex items-center gap-2 text-sm font-semibold">
                <Icon className="h-4 w-4" />
                {MAIL_CATEGORY_LABEL[key]}
                <span className="ml-auto text-xs text-slate-500">{items.length}</span>
              </header>
              {items.length === 0 ? (
                <p className="text-xs text-slate-500">Bu kategoride mail yok.</p>
              ) : (
                <ul className="space-y-1.5">
                  {items.slice(0, 5).map((entry) => (
                    <MailRow key={entry.id} entry={entry} />
                  ))}
                </ul>
              )}
              {extra > 0 && (
                <div className="text-xs text-slate-500">(ve {extra} daha…)</div>
              )}
            </section>
          );
        })}
      </div>
      {data.needs_reply_count > 0 && (
        <button
          type="button"
          onClick={onReplyClick}
          data-testid="mail-reply-prompt"
          className="w-full rounded-lg border border-sky-400/40 bg-sky-500/10 px-4 py-2 text-sm text-sky-200 transition hover:bg-sky-500/20"
        >
          Yanıt bekleyen {data.needs_reply_count} mail var — görmek ister misin?
        </button>
      )}
    </>
  );
}
