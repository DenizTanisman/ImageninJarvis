import { expect, test } from "@playwright/test";

import { mock } from "./helpers/mockApi";

/**
 * Scenario 3 — Calendar create from chat.
 * User types "yarın 14'te toplantı ekle" → backend returns a
 * CalendarEvent payload → MessageBubble renders CalendarEventCard
 * inline with create badge.
 */
test("chat create returns inline CalendarEventCard", async ({ page }) => {
  await mock.authConnected(page);
  await mock.chat(page, () => ({
    ui_type: "CalendarEvent",
    data: {
      id: "evt-1",
      summary: "Q2 review",
      start: "2026-04-29T14:00:00+03:00",
      end: "2026-04-29T15:00:00+03:00",
      description: "",
      html_link: "https://calendar.google.com/event?eid=x",
    },
    meta: {
      action: "create",
      voice_summary: "Tamam, 'Q2 review' kaydedildi.",
    },
  }));

  await page.goto("/chat");

  await page.getByTestId("chat-input").fill("yarın 14'te 1 saatlik Q2 review ekle");
  await page.getByTestId("send-button").click();

  // The voice_summary becomes the bubble headline.
  await expect(page.getByText(/Q2 review.*kaydedildi/)).toBeVisible();

  // The actual rich card lands with create badge + Düzenle / Sil buttons.
  await expect(page.getByTestId("calendar-event-card")).toBeVisible();
  await expect(page.getByText("yeni etkinlik")).toBeVisible();
  await expect(page.getByTestId("calendar-event-edit")).toBeVisible();
  await expect(page.getByTestId("calendar-event-delete")).toBeVisible();
});
