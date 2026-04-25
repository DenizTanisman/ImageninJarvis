import { Inbox, Mail, Megaphone, MessagesSquare } from "lucide-react";
import type { ComponentType, SVGProps } from "react";

import { MailRangeSelector } from "@/components/capability/MailRangeSelector";
import { cn } from "@/lib/utils";
import {
  MAIL_CATEGORY_COLOR,
  MAIL_CATEGORY_LABEL,
  MOCK_MAILS,
  type MailCategoryKey,
  type MailMock,
} from "@/lib/mock-data";

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

function MailRow({ mail }: { mail: MailMock }) {
  return (
    <li className="rounded-md border border-slate-800 bg-slate-900/50 px-3 py-2 text-sm">
      <div className="flex items-baseline justify-between gap-2">
        <span className="truncate font-medium text-slate-100">{mail.from}</span>
        {mail.needsReply && (
          <span className="shrink-0 rounded-full bg-rose-500/20 px-2 py-0.5 text-[10px] uppercase text-rose-200">
            yanıt bekliyor
          </span>
        )}
      </div>
      <div className="truncate text-xs text-slate-300">{mail.subject}</div>
      <div className="line-clamp-2 text-xs text-slate-500">{mail.snippet}</div>
    </li>
  );
}

export function MailCard({ onReplyClick }: MailCardProps) {
  const needsReplyCount = Object.values(MOCK_MAILS)
    .flat()
    .filter((m) => m.needsReply).length;

  return (
    <div data-testid="mail-card" className="space-y-4">
      <MailRangeSelector />
      <div className="grid gap-3 sm:grid-cols-2">
        {ORDER.map((key) => {
          const mails = MOCK_MAILS[key];
          const Icon = CATEGORY_ICON[key];
          const extra = Math.max(0, mails.length - 5);
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
                <span className="ml-auto text-xs text-slate-500">
                  {mails.length}
                </span>
              </header>
              <ul className="space-y-1.5">
                {mails.slice(0, 5).map((mail) => (
                  <MailRow key={mail.id} mail={mail} />
                ))}
              </ul>
              {extra > 0 && (
                <div className="text-xs text-slate-500">(ve {extra} daha…)</div>
              )}
            </section>
          );
        })}
      </div>
      {needsReplyCount > 0 && (
        <button
          type="button"
          onClick={onReplyClick}
          data-testid="mail-reply-prompt"
          className="w-full rounded-lg border border-sky-400/40 bg-sky-500/10 px-4 py-2 text-sm text-sky-200 transition hover:bg-sky-500/20"
        >
          Yanıt bekleyen {needsReplyCount} mail var — görmek ister misin?
        </button>
      )}
    </div>
  );
}
