import { expect, test } from "@playwright/test";

import { mock } from "./helpers/mockApi";
import { installSpeechStubs, speak } from "./helpers/voice";

/**
 * Scenario 5 — Voice-mode mail.
 * Stub the Web Speech surface, navigate to /voice, fire a final
 * transcript, and assert that the dispatcher pipeline routes through
 * to a MailCard payload AND the TTS surface speaks the voice_summary.
 */
test("voice transcript triggers mail summary + TTS speaks the digest", async ({
  page,
}) => {
  await installSpeechStubs(page);
  await mock.chat(page, () => ({
    ui_type: "MailCard",
    data: {
      range: { kind: "daily", after: "2026-04-28", before: "2026-04-29" },
      categories: {
        important: [
          {
            id: "m1",
            from: "Test User",
            subject: "Hi",
            snippet: "...",
            summary: "Önemli bir mail.",
            needs_reply: false,
            confidence: 0.9,
            thread_id: "t1",
          },
        ],
        dm: [],
        promo: [],
        other: [],
      },
      needs_reply_count: 0,
      total: 1,
    },
    meta: {
      voice_summary:
        "1 önemli mail var. Yanıt bekleyen yok.",
    },
  }));

  await page.goto("/voice");

  // Mic auto-starts; status should reflect that.
  await expect(page.getByTestId("voice-status")).toBeVisible();

  // Drive a final transcript.
  await speak(page, "bugünün maillerini özetle");

  // After the dispatcher round-trip, the assistant response is spoken.
  // We verify TTS by reading the test bridge.
  await expect
    .poll(
      () =>
        page.evaluate(
          () =>
            (
              window as unknown as {
                __voiceTest: { spoken: string[] };
              }
            ).__voiceTest.spoken,
        ),
      { timeout: 5000 },
    )
    .toContain("1 önemli mail var. Yanıt bekleyen yok.");

  // Switch to chat — the conversation history carries the rich payload,
  // so the inline MailCard now renders.
  await page.getByTestId("switch-to-chat").click();
  await expect(page.getByTestId("mail-card")).toBeVisible();
});
