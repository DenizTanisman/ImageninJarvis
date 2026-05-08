export type MailCategoryKey = "important" | "dm" | "promo" | "other";

export interface MailMock {
  id: string;
  from: string;
  subject: string;
  snippet: string;
  needsReply?: boolean;
}

export const MAIL_CATEGORY_LABEL: Record<MailCategoryKey, string> = {
  important: "Important",
  dm: "DM",
  promo: "Promo",
  other: "Other",
};

export const MAIL_CATEGORY_COLOR: Record<MailCategoryKey, string> = {
  important: "text-rose-300 ring-rose-400/30",
  dm: "text-sky-300 ring-sky-400/30",
  promo: "text-amber-300 ring-amber-400/30",
  other: "text-slate-300 ring-slate-500/30",
};

export const MOCK_MAILS: Record<MailCategoryKey, MailMock[]> = {
  important: [
    {
      id: "m1",
      from: "Test User",
      subject: "About tomorrow's meeting",
      snippet: "Can we go over the agenda for 2 PM?",
      needsReply: true,
    },
    {
      id: "m2",
      from: "Sample Project",
      subject: "Q2 goals draft",
      snippet: "Could you review the attached draft and get back to me?",
      needsReply: true,
    },
  ],
  dm: [
    {
      id: "m3",
      from: "ops@example.com",
      subject: "Quick question",
      snippet: "Could you quickly verify a parameter?",
      needsReply: true,
    },
  ],
  promo: [
    {
      id: "m4",
      from: "Newsletter",
      subject: "What changed in April?",
      snippet: "This month's updates…",
    },
    {
      id: "m5",
      from: "Store",
      subject: "20% discount opportunity",
      snippet: "Today-only campaign.",
    },
  ],
  other: [
    {
      id: "m6",
      from: "system@example.com",
      subject: "Weekly report",
      snippet: "Your usage summary report is ready.",
    },
  ],
};

export interface TranslationMock {
  sourceLang: string;
  targetLang: string;
  source: string;
  target: string;
}

export const MOCK_TRANSLATION: TranslationMock = {
  sourceLang: "tr",
  targetLang: "en",
  source: "Merhaba, bugün nasıl yardımcı olabilirim?",
  target: "Hello, how can I help you today?",
};

export const TRANSLATION_LANGS = [
  { code: "tr", label: "Türkçe" },
  { code: "en", label: "English" },
  { code: "de", label: "Deutsch" },
  { code: "fr", label: "Français" },
  { code: "es", label: "Español" },
  { code: "ru", label: "Русский" },
  { code: "ar", label: "العربية" },
];

export interface EventMock {
  id: string;
  title: string;
  date: string;
  time: string;
  detail: string;
}

export const MOCK_EVENTS: EventMock[] = [
  {
    id: "e1",
    title: "Product meeting",
    date: "2026-04-28",
    time: "14:00 – 15:00",
    detail: "Q2 sprint plan and milestone review.",
  },
  {
    id: "e2",
    title: "Sample Project sync",
    date: "2026-04-29",
    time: "10:00 – 10:30",
    detail: "Weekly update with Test User.",
  },
  {
    id: "e3",
    title: "Design review",
    date: "2026-05-02",
    time: "16:00 – 17:00",
    detail: "Design critique of the new onboarding flow.",
  },
];

export interface DriveFileMock {
  id: string;
  name: string;
  mimeType: "application/pdf" | "text/plain";
  size: string;
}

export const MOCK_DRIVE_FILES: DriveFileMock[] = [
  { id: "d1", name: "quarterly-plan.pdf", mimeType: "application/pdf", size: "420 KB" },
  { id: "d2", name: "notes.txt", mimeType: "text/plain", size: "4 KB" },
  { id: "d3", name: "design-review.pdf", mimeType: "application/pdf", size: "1.2 MB" },
];
