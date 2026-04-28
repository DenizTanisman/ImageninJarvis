import { Loader2, Mail, Send, X } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import {
  ChatNetworkError,
  getAuthStatus,
  googleConnectUrl,
  sendNewMail,
  type AuthStatus,
  type MailDraftCardData,
} from "@/api/client";
import { cn } from "@/lib/utils";

interface MailDraftCardProps {
  data: MailDraftCardData;
}

type Phase =
  | { kind: "draft" }
  | { kind: "confirm" }
  | { kind: "sending" }
  | { kind: "sent"; messageId: string | null }
  | { kind: "cancelled" }
  | { kind: "error"; message: string };

export function MailDraftCard({ data }: MailDraftCardProps) {
  const [to, setTo] = useState(data.to);
  const [subject, setSubject] = useState(data.subject);
  const [body, setBody] = useState(data.body);
  const [phase, setPhase] = useState<Phase>({ kind: "draft" });
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);

  // Probe auth status once so we can short-circuit Gönder if the user
  // hasn't granted gmail.send. We don't block render — they can still
  // edit the draft; we only gate the send action.
  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    getAuthStatus(controller.signal)
      .then((status) => {
        if (!cancelled) setAuthStatus(status);
      })
      .catch(() => {
        // Auth probe failure isn't fatal — user can still edit; the
        // send call itself will surface a friendly 401/403.
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  const startSend = () => {
    if (!to.trim() || !to.includes("@")) {
      toast.error("Geçerli bir alıcı adresi yaz.", { duration: 2500 });
      return;
    }
    if (!body.trim()) {
      toast.error("Mail gövdesi boş olamaz.", { duration: 2500 });
      return;
    }
    setPhase({ kind: "confirm" });
  };

  const confirmSend = async () => {
    setPhase({ kind: "sending" });
    try {
      const response = await sendNewMail({
        to: to.trim(),
        subject: subject.trim(),
        body: body.trim(),
      });
      if (response.error) {
        setPhase({ kind: "error", message: response.error.user_message });
        toast.error(response.error.user_message, { duration: 3000 });
        return;
      }
      toast.success("Mail gönderildi.", { duration: 2500 });
      setPhase({ kind: "sent", messageId: response.sent_message_id });
    } catch (err) {
      const message =
        err instanceof ChatNetworkError ? err.message : "Mail gönderilemedi.";
      setPhase({ kind: "error", message });
      toast.error(message, { duration: 3000 });
    }
  };

  if (phase.kind === "sent") {
    return (
      <div
        data-testid="mail-draft-card"
        className="rounded-xl border border-emerald-400/40 bg-emerald-500/10 p-3 text-sm text-emerald-100"
      >
        <div className="flex items-center gap-2">
          <Mail className="h-4 w-4" />
          Mail <span className="font-semibold">{to}</span> adresine gönderildi.
        </div>
      </div>
    );
  }

  if (phase.kind === "cancelled") {
    return (
      <div
        data-testid="mail-draft-card"
        className="rounded-xl border border-slate-800 bg-slate-900/40 p-3 text-xs text-slate-500"
      >
        Taslak iptal edildi.
      </div>
    );
  }

  const sending = phase.kind === "sending";
  const showAuthGate = authStatus && !authStatus.can_send;

  return (
    <div
      data-testid="mail-draft-card"
      className="space-y-2 rounded-xl border border-sky-400/30 bg-slate-900/50 p-3"
    >
      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-sky-300/80">
        <Mail className="h-3 w-3" />
        Yeni mail taslağı
      </div>

      <Field
        label="Kime"
        testId="draft-to"
        value={to}
        onChange={setTo}
        disabled={sending}
      />
      <Field
        label="Konu"
        testId="draft-subject"
        value={subject}
        onChange={setSubject}
        disabled={sending}
        placeholder="(konusuz)"
      />
      <label className="flex flex-col gap-1 text-xs text-slate-400">
        Gövde
        <textarea
          data-testid="draft-body"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          disabled={sending}
          rows={6}
          className="resize-y rounded-md border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-400 disabled:opacity-50"
        />
      </label>

      {showAuthGate && (
        <div className="space-y-2 rounded-md border border-amber-400/40 bg-amber-500/10 p-2 text-xs text-amber-100">
          <p>Mail gönderme izni yok. Tekrar bağlanıp send iznini de ver.</p>
          <a
            href={googleConnectUrl()}
            target="_blank"
            rel="noopener noreferrer"
            data-testid="draft-reconnect"
            className="inline-flex items-center gap-1 rounded bg-sky-500 px-2 py-1 text-xs font-semibold text-white hover:bg-sky-400"
          >
            Google'a tekrar bağlan
          </a>
        </div>
      )}

      {phase.kind === "error" && (
        <div
          data-testid="draft-error"
          className="rounded-md border border-rose-400/40 bg-rose-500/10 p-2 text-xs text-rose-100"
        >
          {phase.message}
        </div>
      )}

      <div className="flex justify-end gap-2 pt-1">
        <button
          type="button"
          onClick={() => setPhase({ kind: "cancelled" })}
          data-testid="draft-cancel"
          disabled={sending}
          className="flex items-center gap-1 rounded px-3 py-1 text-xs text-slate-300 transition hover:bg-slate-800 disabled:opacity-50"
        >
          <X className="h-3 w-3" />
          İptal
        </button>
        <button
          type="button"
          onClick={startSend}
          data-testid="draft-send"
          disabled={sending || Boolean(showAuthGate)}
          className={cn(
            "flex items-center gap-2 rounded bg-sky-500 px-3 py-1 text-xs font-semibold text-white transition hover:bg-sky-400",
            (sending || showAuthGate) &&
              "cursor-not-allowed bg-slate-800 text-slate-400 hover:bg-slate-800",
          )}
        >
          {sending ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <Send className="h-3 w-3" />
          )}
          Gönder
        </button>
      </div>

      {phase.kind === "confirm" && (
        <ConfirmSendDialog
          to={to}
          subject={subject}
          onCancel={() => setPhase({ kind: "draft" })}
          onConfirm={() => void confirmSend()}
        />
      )}
    </div>
  );
}

interface FieldProps {
  label: string;
  testId: string;
  value: string;
  onChange: (next: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

function Field({ label, testId, value, onChange, disabled, placeholder }: FieldProps) {
  return (
    <label className="flex flex-col gap-1 text-xs text-slate-400">
      {label}
      <input
        data-testid={testId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        placeholder={placeholder}
        className="rounded-md border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-400 disabled:opacity-50"
      />
    </label>
  );
}

interface ConfirmSendDialogProps {
  to: string;
  subject: string;
  onCancel: () => void;
  onConfirm: () => void;
}

function ConfirmSendDialog({
  to,
  subject,
  onCancel,
  onConfirm,
}: ConfirmSendDialogProps) {
  return (
    <div
      data-testid="draft-confirm"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div className="w-full max-w-md rounded-xl border border-slate-800 bg-slate-950 p-4 shadow-xl">
        <div className="mb-2 text-sm font-semibold text-slate-100">
          Mail göndereyim mi?
        </div>
        <p className="text-sm text-slate-300">
          <span className="font-semibold text-slate-100">{to}</span> adresine{" "}
          {subject ? (
            <>
              <span className="font-semibold text-slate-100">"{subject}"</span>{" "}
              başlıklı
            </>
          ) : (
            "konusuz"
          )}{" "}
          maili göndermek üzeresin. Gönderdikten sonra geri alınamaz.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            data-testid="draft-confirm-cancel"
            className="rounded px-3 py-1 text-xs text-slate-300 hover:text-slate-100"
          >
            Vazgeç
          </button>
          <button
            type="button"
            onClick={onConfirm}
            data-testid="draft-confirm-yes"
            className="flex items-center gap-1 rounded bg-sky-500 px-3 py-1 text-xs font-semibold text-white hover:bg-sky-400"
          >
            <Send className="h-3 w-3" />
            Evet, gönder
          </button>
        </div>
      </div>
    </div>
  );
}
