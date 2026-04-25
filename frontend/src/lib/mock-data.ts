export type MailCategoryKey = "important" | "dm" | "promo" | "other";

export interface MailMock {
  id: string;
  from: string;
  subject: string;
  snippet: string;
  needsReply?: boolean;
}

export const MAIL_CATEGORY_LABEL: Record<MailCategoryKey, string> = {
  important: "Önemli",
  dm: "DM",
  promo: "Promo",
  other: "Diğer",
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
      subject: "Yarınki toplantı hakkında",
      snippet: "Saat 14:00 için ajandayı gözden geçirebilir miyiz?",
      needsReply: true,
    },
    {
      id: "m2",
      from: "Sample Project",
      subject: "Q2 hedefleri taslağı",
      snippet: "Ek'te bulunan taslağı inceleyip dönüş yapar mısın?",
      needsReply: true,
    },
  ],
  dm: [
    {
      id: "m3",
      from: "ops@example.com",
      subject: "Kısa bir soru",
      snippet: "Hızlıca bir parametreyi doğrulayabilir misin?",
      needsReply: true,
    },
  ],
  promo: [
    {
      id: "m4",
      from: "Newsletter",
      subject: "Nisan'da neler değişti?",
      snippet: "Bu ayın yenilikleri…",
    },
    {
      id: "m5",
      from: "Store",
      subject: "%20 indirim fırsatı",
      snippet: "Sadece bugüne özel kampanya.",
    },
  ],
  other: [
    {
      id: "m6",
      from: "system@example.com",
      subject: "Haftalık rapor",
      snippet: "Kullanım özeti raporunuz hazır.",
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
    title: "Ürün toplantısı",
    date: "2026-04-28",
    time: "14:00 – 15:00",
    detail: "Q2 sprint planı ve milestone değerlendirmesi.",
  },
  {
    id: "e2",
    title: "Sample Project sync",
    date: "2026-04-29",
    time: "10:00 – 10:30",
    detail: "Test User ile haftalık güncelleme.",
  },
  {
    id: "e3",
    title: "Tasarım incelemesi",
    date: "2026-05-02",
    time: "16:00 – 17:00",
    detail: "Yeni onboarding akışının tasarım kritiği.",
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
