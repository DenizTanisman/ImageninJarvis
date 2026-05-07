import { ChevronDown, ChevronRight, Inbox, Loader2, Mail, Megaphone, MessagesSquare } from "lucide-react";
import { useEffect, useState } from "react";
import type { ComponentType, SVGProps } from "react";

import {
  ChatNetworkError,
  fetchMailMessage,
  fetchMailSummary,
  getAuthStatus,
  googleConnectUrl,
  type AuthStatus,
  type MailEntry,
  type MailMessageDetail,
  type MailSummaryData,
} from "@/api/client";
import { BatchReplyView } from "@/components/capability/BatchReplyView";
import { MailDraftCard } from "@/components/capability/MailDraftCard";
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
  /** When provided, MailCard skips the mail fetch and renders this data
   * directly. Used by the chat surface to render an inline summary that
   * was returned from the dispatcher rather than fetched on-demand. */
  initialData?: MailSummaryData;
  /** Hide the daily/custom/compose range buttons. The chat-rendered
   * inline view shows a snapshot tied to the user's question, so letting
   * them switch ranges would be misleading. */
  hideRangeSelector?: boolean;
}

type DetailState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; detail: MailMessageDetail }
  | { kind: "error"; message: string };

const COLLAPSED_LIMIT = 5;

function CategorySection({
  categoryKey,
  items,
}: {
  categoryKey: MailCategoryKey;
  items: MailEntry[];
}) {
  const [showAll, setShowAll] = useState(false);
  const Icon = CATEGORY_ICON[categoryKey];
  const visible = showAll ? items : items.slice(0, COLLAPSED_LIMIT);
  const hidden = Math.max(0, items.length - COLLAPSED_LIMIT);
  return (
    <section
      data-testid={`mail-cat-${categoryKey}`}
      className={cn(
        "space-y-2 rounded-xl border border-slate-800 bg-slate-950/50 p-3 ring-1",
        MAIL_CATEGORY_COLOR[categoryKey],
      )}
    >
      <header className="flex items-center gap-2 text-sm font-semibold">
        <Icon className="h-4 w-4" />
        {MAIL_CATEGORY_LABEL[categoryKey]}
        <span className="ml-auto text-xs text-slate-500">{items.length}</span>
      </header>
      {items.length === 0 ? (
        <p className="text-xs text-slate-500">Bu kategoride mail yok.</p>
      ) : (
        <ul className="space-y-1.5">
          {visible.map((entry) => (
            <MailRow key={entry.id} entry={entry} />
          ))}
        </ul>
      )}
      {hidden > 0 && (
        <button
          type="button"
          onClick={() => setShowAll((v) => !v)}
          data-testid={`mail-cat-${categoryKey}-toggle`}
          className="w-full rounded-md border border-slate-700/60 bg-slate-900/40 px-2 py-1 text-xs text-slate-300 transition hover:border-sky-400/40 hover:text-sky-200"
        >
          {showAll ? "Daha az göster" : `(ve ${hidden} daha — tümünü göster)`}
        </button>
      )}
    </section>
  );
}

function MailRow({ entry }: { entry: MailEntry }) {
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<DetailState>({ kind: "idle" });

  const toggle = () => {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    if (detail.kind === "idle") {
      setDetail({ kind: "loading" });
      const controller = new AbortController();
      fetchMailMessage(entry.id, controller.signal)
        .then((d) => setDetail({ kind: "ready", detail: d }))
        .catch((e: unknown) => {
          const message =
            e instanceof ChatNetworkError ? e.message : "Mail içeriği alınamadı.";
          setDetail({ kind: "error", message });
        });
    }
  };

  return (
    <li className="rounded-md border border-slate-800 bg-slate-900/50 text-sm">
      <button
        type="button"
        onClick={toggle}
        data-testid={`mail-row-${entry.id}`}
        aria-expanded={open}
        className="flex w-full items-start gap-2 px-3 py-2 text-left transition hover:bg-slate-900"
      >
        <span className="mt-0.5 shrink-0 text-slate-400">
          {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-baseline justify-between gap-2">
            <span className="truncate font-medium text-slate-100">{entry.from}</span>
            {entry.needs_reply && (
              <span className="shrink-0 rounded-full bg-rose-500/20 px-2 py-0.5 text-[10px] uppercase text-rose-200">
                yanıt bekliyor
              </span>
            )}
          </span>
          <span className="block truncate text-xs text-slate-300">{entry.subject}</span>
          {!open && (
            <span className="block line-clamp-2 text-xs text-slate-500">
              {entry.summary || entry.snippet}
            </span>
          )}
        </span>
      </button>

      {open && (
        <div className="border-t border-slate-800 px-3 py-2 text-xs text-slate-300">
          {entry.summary && (
            <p className="mb-2 italic text-slate-400">
              <span className="text-slate-500">Özet:</span> {entry.summary}
            </p>
          )}
          {detail.kind === "loading" && (
            <div className="flex items-center gap-2 text-slate-500">
              <Loader2 className="h-3 w-3 animate-spin" /> Tam içerik yükleniyor…
            </div>
          )}
          {detail.kind === "error" && (
            <div className="rounded border border-rose-400/30 bg-rose-500/10 p-2 text-rose-200">
              {detail.message}
            </div>
          )}
          {detail.kind === "ready" && (
            <pre className="max-h-96 overflow-y-auto whitespace-pre-wrap break-words font-sans text-xs text-slate-200">
              {detail.detail.body || detail.detail.snippet || "(içerik yok)"}
            </pre>
          )}
        </div>
      )}
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

export function MailCard({
  onReplyClick,
  initialData,
  hideRangeSelector,
}: MailCardProps) {
  const range = useMailUI((s) => s.range);
  const [state, setState] = useState<LoadState>({ kind: "idle" });
  const [view, setView] = useState<ViewMode>("list");

  // Re-fetch whenever the range changes (kind switch or custom date edit).
  // When `initialData` is supplied, skip the fetch and only resolve auth
  // status (needed to enable the batch-reply path).
  // The `compose` range kind is handled separately below — it short-
  // circuits both fetch paths so the user can edit a blank draft without
  // touching Gmail.
  useEffect(() => {
    if (range.kind === "compose") {
      // Nothing to load. Render a blank draft directly.
      setState({ kind: "idle" });
      setView("list");
      return;
    }

    let cancelled = false;
    const controller = new AbortController();

    async function loadFromBackend() {
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
        // The compose path is short-circuited above; daily and custom are
        // the only kinds that ever reach the fetch.
        const fetchKind: "daily" | "custom" =
          range.kind === "custom" ? "custom" : "daily";
        const result = await fetchMailSummary(
          { range_kind: fetchKind, ...bounds, max_results: 30 },
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

    async function loadAuthOnly(data: MailSummaryData) {
      setState({ kind: "loading" });
      setView("list");
      try {
        const status = await getAuthStatus(controller.signal);
        if (cancelled) return;
        setState({ kind: "ready", data, authStatus: status, cached: false });
      } catch {
        if (cancelled) return;
        // Auth probe failure shouldn't hide the summary the user already
        // has — fall back to a disconnected stub so the categories still
        // render. Batch-reply UI will surface the auth issue if pressed.
        setState({
          kind: "ready",
          data,
          authStatus: { connected: false, scopes: [], can_send: false },
          cached: false,
        });
      }
    }

    if (initialData) {
      void loadAuthOnly(initialData);
    } else {
      void loadFromBackend();
    }
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [range, initialData]);

  const handleReplyClick = () => {
    onReplyClick?.();
    setView("reply");
  };

  return (
    <div data-testid="mail-card" className="space-y-4">
      {view === "list" && !hideRangeSelector && <MailRangeSelector />}
      {range.kind === "compose" && !hideRangeSelector ? (
        // Compose mode: blank draft. The user fills To / Subject / Body
        // and the existing MailDraftCard handles confirm + send + auth
        // gating. Resetting `data.to` to an empty string each render is
        // intentional — picking the tab again should give a fresh draft.
        <MailDraftCard data={{ to: "", subject: "", body: "" }} />
      ) : (
        <Body
          state={state}
          view={view}
          onReplyClick={handleReplyClick}
          onBackToList={() => setView("list")}
        />
      )}
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
        {ORDER.map((key) => (
          <CategorySection key={key} categoryKey={key} items={data.categories[key] ?? []} />
        ))}
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
