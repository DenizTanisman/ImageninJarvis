import { expect, test } from "@playwright/test";

import { mock } from "./helpers/mockApi";

/**
 * Scenario 2 — Mail batch reply.
 * Open Mail shortcut → summary loads → "yanıt bekleyen" prompt →
 * generate drafts → confirm send.
 */
test("mail batch reply: summary → drafts → confirm send", async ({ page }) => {
  await mock.authConnected(page);
  await mock.mailSummary(page, {
    range: { kind: "daily", after: "2026-04-28", before: "2026-04-29" },
    categories: {
      important: [
        {
          id: "m1",
          from: "Test User <test@example.com>",
          subject: "Yarınki toplantı",
          snippet: "Saat 14:00 hâlâ uygun mu?",
          summary: "Saat 14:00 hâlâ uygun mu?",
          needs_reply: true,
          confidence: 0.95,
          thread_id: "t1",
        },
      ],
      dm: [],
      promo: [],
      other: [],
    },
    needs_reply_count: 1,
    total: 1,
  });
  await mock.drafts(page, [
    {
      message_id: "m1",
      thread_id: "t1",
      to: "test@example.com",
      subject: "Yarınki toplantı",
      body: "Merhaba,\n\nSaat 14:00 benim için uygun.\n\nİyi çalışmalar.",
    },
  ]);
  await mock.sendDraft(page);

  await page.goto("/chat");
  await page.getByTestId("shortcut-mail").click();

  // Summary card lands; the prompt button shows the needs-reply count.
  await expect(page.getByTestId("mail-card")).toBeVisible();
  await expect(page.getByTestId("mail-reply-prompt")).toBeVisible();
  await page.getByTestId("mail-reply-prompt").click();

  // Pick the (only) needs_reply mail and continue to draft review.
  await page.getByTestId("reply-toggle-m1").check();
  await page.getByTestId("reply-continue").click();

  // Draft preview appears with the mocked body in an editable textarea.
  await expect(page.getByTestId("reply-body-m1")).toHaveValue(
    /Saat 14:00 benim için uygun\./,
  );

  // Approve sends immediately — Onayla & gönder is the explicit confirm.
  await page.getByTestId("reply-approve-m1").click();

  // The card row transitions to a "Gönderildi" status badge.
  await expect(page.getByText(/Gönderildi/).first()).toBeVisible();
});
