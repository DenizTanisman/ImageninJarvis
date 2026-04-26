import { Check, Loader2, Send, Undo2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import {
  ChatNetworkError,
  generateDrafts,
  googleConnectUrl,
  sendDraft,
  type AuthStatus,
  type MailEntry,
  type MailSummaryData,
  type ReplyDraftDTO,
} from "@/api/client";
import { cn } from "@/lib/utils";

interface BatchReplyViewProps {
  summary: MailSummaryData;
  authStatus: AuthStatus;
  onClose: () => void;
}

interface DraftRow extends ReplyDraftDTO {
  status: "pending" | "sending" | "sent" | "skipped" | "failed";
  edited: boolean;
}

type Phase =
  | { kind: "select" }
  | { kind: "loading-drafts" }
  | { kind: "review"; drafts: DraftRow[] }
  | { kind: "error"; message: string };

function flatNeedsReply(summary: MailSummaryData): MailEntry[] {
  const all = [
    ...summary.categories.important,
    ...summary.categories.dm,
    ...summary.categories.promo,
    ...summary.categories.other,
  ];
  return all.filter((m) => m.needs_reply);
}

export function BatchReplyView({
  summary,
  authStatus,
  onClose,
}: BatchReplyViewProps) {
  const candidates = flatNeedsReply(summary);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(
    () => new Set(candidates.map((c) => c.id)),
  );
  const [phase, setPhase] = useState<Phase>({ kind: "select" });

  if (!authStatus.can_send) {
    return (
      <div
        data-testid="reply-needs-send-scope"
        className="space-y-3 rounded-xl border border-amber-400/40 bg-amber-500/10 p-4 text-sm text-amber-100"
      >
        <p>
          Mail göndermek için Google bağlantını yenileyip{" "}
          <code>gmail.send</code> iznini de vermen lazım.
        </p>
        <a
          href={googleConnectUrl()}
          target="_blank"
          rel="noopener noreferrer"
          data-testid="reply-reconnect"
          className="inline-flex items-center gap-2 rounded-lg bg-sky-500 px-3 py-2 text-xs font-semibold text-white transition hover:bg-sky-400"
        >
          Tekrar Google'a bağlan
        </a>
      </div>
    );
  }

  if (candidates.length === 0) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-sm text-slate-300">
        Şu an yanıt bekleyen mail yok.
      </div>
    );
  }

  const toggle = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const startDrafts = async () => {
    if (selectedIds.size === 0) return;
    setPhase({ kind: "loading-drafts" });
    try {
      const response = await generateDrafts(Array.from(selectedIds));
      if (response.drafts.length === 0) {
        setPhase({
          kind: "error",
          message:
            response.failures.length > 0
              ? "Hiçbir taslak üretilemedi, biraz sonra dener misin?"
              : "Seçili mailler için taslak alınamadı.",
        });
        return;
      }
      setPhase({
        kind: "review",
        drafts: response.drafts.map((d) => ({
          ...d,
          status: "pending" as const,
          edited: false,
        })),
      });
      if (response.failures.length > 0) {
        toast.info(
          `${response.failures.length} mail için taslak üretilemedi.`,
          { duration: 2500 },
        );
      }
    } catch (err) {
      const message =
        err instanceof ChatNetworkError ? err.message : "Beklenmeyen bir hata.";
      setPhase({ kind: "error", message });
    }
  };

  if (phase.kind === "select") {
    return (
      <SelectStep
        candidates={candidates}
        selectedIds={selectedIds}
        onToggle={toggle}
        onCancel={onClose}
        onContinue={startDrafts}
      />
    );
  }

  if (phase.kind === "loading-drafts") {
    return (
      <div
        data-testid="reply-loading"
        className="flex items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-8 text-sm text-slate-400"
      >
        <Loader2 className="h-4 w-4 animate-spin text-sky-300" />
        Taslaklar üretiliyor…
      </div>
    );
  }

  if (phase.kind === "error") {
    return (
      <div
        data-testid="reply-error"
        className="space-y-3 rounded-xl border border-rose-400/40 bg-rose-500/10 p-4 text-sm text-rose-100"
      >
        <p>{phase.message}</p>
        <button
          type="button"
          onClick={onClose}
          className="rounded bg-slate-800 px-3 py-1 text-xs text-slate-200"
        >
          Kapat
        </button>
      </div>
    );
  }

  return (
    <ReviewStep
      drafts={phase.drafts}
      onUpdate={(next) => setPhase({ kind: "review", drafts: next })}
      onClose={onClose}
    />
  );
}

interface SelectStepProps {
  candidates: MailEntry[];
  selectedIds: Set<string>;
  onToggle: (id: string) => void;
  onContinue: () => void;
  onCancel: () => void;
}

function SelectStep({
  candidates,
  selectedIds,
  onToggle,
  onContinue,
  onCancel,
}: SelectStepProps) {
  return (
    <div data-testid="reply-select" className="space-y-3">
      <p className="text-sm text-slate-300">
        Cevaplamak istediklerini işaretle. Her mail için taslağı tek tek
        onaylayacaksın.
      </p>
      <ul className="space-y-2">
        {candidates.map((entry) => {
          const checked = selectedIds.has(entry.id);
          return (
            <li
              key={entry.id}
              data-testid={`reply-candidate-${entry.id}`}
              className={cn(
                "rounded-lg border px-3 py-2 text-sm transition",
                checked
                  ? "border-sky-400 bg-sky-500/10"
                  : "border-slate-700 bg-slate-900/40",
              )}
            >
              <label className="flex cursor-pointer items-start gap-3">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggle(entry.id)}
                  data-testid={`reply-toggle-${entry.id}`}
                  className="mt-1 h-4 w-4 rounded border-slate-600 bg-slate-900"
                />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-slate-100">{entry.from}</div>
                  <div className="truncate text-xs text-slate-300">
                    {entry.subject}
                  </div>
                  <div className="line-clamp-2 text-xs text-slate-500">
                    {entry.summary || entry.snippet}
                  </div>
                </div>
              </label>
            </li>
          );
        })}
      </ul>

      <div className="flex justify-end gap-2 border-t border-slate-800 pt-3">
        <button
          type="button"
          onClick={onCancel}
          className="rounded px-3 py-1 text-xs text-slate-300 hover:text-slate-100"
        >
          Vazgeç
        </button>
        <button
          type="button"
          data-testid="reply-continue"
          disabled={selectedIds.size === 0}
          onClick={onContinue}
          className="rounded bg-sky-500 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
        >
          Seçileni cevapla ({selectedIds.size})
        </button>
      </div>
    </div>
  );
}

interface ReviewStepProps {
  drafts: DraftRow[];
  onUpdate: (next: DraftRow[]) => void;
  onClose: () => void;
}

function ReviewStep({ drafts, onUpdate, onClose }: ReviewStepProps) {
  // Auto-close once every draft has reached a terminal status.
  useEffect(() => {
    if (
      drafts.every((d) =>
        ["sent", "skipped", "failed"].includes(d.status),
      )
    ) {
      // Defer slightly so the last status badge animates in first.
      const handle = window.setTimeout(onClose, 1500);
      return () => window.clearTimeout(handle);
    }
  }, [drafts, onClose]);

  const updateRow = (index: number, patch: Partial<DraftRow>) => {
    const copy = drafts.slice();
    copy[index] = { ...copy[index], ...patch };
    onUpdate(copy);
  };

  const approveSend = async (index: number) => {
    const draft = drafts[index];
    if (draft.status !== "pending") return;
    updateRow(index, { status: "sending" });
    try {
      const response = await sendDraft(draft);
      if (response.sent_message_id) {
        updateRow(index, { status: "sent" });
        toast.success("Mail gönderildi.", { duration: 2500 });
      } else {
        updateRow(index, { status: "failed" });
        toast.error(response.error?.user_message ?? "Mail gönderilemedi.", {
          duration: 3000,
        });
      }
    } catch (err) {
      updateRow(index, { status: "failed" });
      const message =
        err instanceof ChatNetworkError ? err.message : "Beklenmeyen hata.";
      toast.error(message, { duration: 3000 });
    }
  };

  return (
    <div data-testid="reply-review" className="space-y-4">
      <p className="text-sm text-slate-300">
        Her taslağı düzenleyebilirsin. Onay olmadan hiçbir mail gönderilmez.
      </p>
      {drafts.map((draft, index) => (
        <DraftCard
          key={draft.message_id}
          draft={draft}
          onBodyChange={(body) =>
            updateRow(index, { body, edited: body !== draft.body })
          }
          onApprove={() => approveSend(index)}
          onSkip={() => updateRow(index, { status: "skipped" })}
        />
      ))}
      <div className="flex justify-end">
        <button
          type="button"
          onClick={onClose}
          className="rounded px-3 py-1 text-xs text-slate-400 hover:text-slate-100"
        >
          Kapat
        </button>
      </div>
    </div>
  );
}

interface DraftCardProps {
  draft: DraftRow;
  onBodyChange: (body: string) => void;
  onApprove: () => void;
  onSkip: () => void;
}

function DraftCard({ draft, onBodyChange, onApprove, onSkip }: DraftCardProps) {
  const isTerminal = ["sent", "skipped", "failed"].includes(draft.status);
  const statusBadge = (() => {
    switch (draft.status) {
      case "sending":
        return (
          <span className="flex items-center gap-1 text-xs text-sky-300">
            <Loader2 className="h-3 w-3 animate-spin" />
            Gönderiliyor…
          </span>
        );
      case "sent":
        return (
          <span className="flex items-center gap-1 text-xs text-emerald-300">
            <Check className="h-3 w-3" />
            Gönderildi
          </span>
        );
      case "skipped":
        return (
          <span className="flex items-center gap-1 text-xs text-slate-400">
            <Undo2 className="h-3 w-3" />
            Atlandı
          </span>
        );
      case "failed":
        return (
          <span className="flex items-center gap-1 text-xs text-rose-300">
            <X className="h-3 w-3" />
            Başarısız
          </span>
        );
      default:
        return null;
    }
  })();

  return (
    <div
      data-testid={`reply-draft-${draft.message_id}`}
      className={cn(
        "space-y-2 rounded-xl border p-3",
        draft.status === "sent"
          ? "border-emerald-400/40 bg-emerald-500/10"
          : draft.status === "skipped"
            ? "border-slate-700 bg-slate-900/40 opacity-70"
            : draft.status === "failed"
              ? "border-rose-400/40 bg-rose-500/10"
              : "border-slate-700 bg-slate-900/60",
      )}
    >
      <div className="flex items-baseline justify-between gap-2 text-xs text-slate-400">
        <div className="truncate">
          <span className="text-slate-200">{draft.to}</span> ·{" "}
          <span className="italic">{draft.subject}</span>
        </div>
        {statusBadge}
      </div>
      <textarea
        value={draft.body}
        readOnly={isTerminal || draft.status === "sending"}
        onChange={(e) => onBodyChange(e.target.value)}
        data-testid={`reply-body-${draft.message_id}`}
        rows={6}
        className="w-full resize-none rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-400"
      />
      {!isTerminal && (
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onSkip}
            data-testid={`reply-skip-${draft.message_id}`}
            disabled={draft.status === "sending"}
            className="rounded px-3 py-1 text-xs text-slate-400 hover:text-slate-200 disabled:cursor-not-allowed"
          >
            Atla
          </button>
          <button
            type="button"
            onClick={onApprove}
            data-testid={`reply-approve-${draft.message_id}`}
            disabled={draft.status === "sending" || draft.body.trim().length === 0}
            className="flex items-center gap-1 rounded bg-sky-500 px-3 py-1 text-xs font-semibold text-white transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
          >
            <Send className="h-3 w-3" />
            Onayla & gönder
          </button>
        </div>
      )}
    </div>
  );
}
