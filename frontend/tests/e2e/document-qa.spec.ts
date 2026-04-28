import { expect, test } from "@playwright/test";

import { mock } from "./helpers/mockApi";

/**
 * Scenario 4 — Document Q&A.
 * Upload a tiny TXT through the modal → close the modal → ask in chat
 * → the question routes to /document via the active-doc context, and
 * the bubble shows the mocked answer.
 */
test("upload then ask in chat routes through document context", async ({
  page,
}) => {
  await mock.upload(page, {
    doc_id: "doc-1",
    page_count: 2,
    original_name: "notes.txt",
    mime_type: "text/plain",
    size_bytes: 128,
  });
  await mock.documentAsk(page, (q) =>
    q.toLowerCase().includes("ne hakkında")
      ? "Bu belge örnek bir kısa nottur ve test amaçlıdır."
      : "Belgeden bir cevap çıkmadı.",
  );

  await page.goto("/chat");
  await page.getByTestId("shortcut-document").click();

  // Upload the file via the hidden input — the dropzone exposes it.
  await page.getByTestId("upload-input").setInputFiles({
    name: "notes.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Bu belge örnek bir kısa nottur."),
  });

  // The DocumentCard transitions to ready state with the file name.
  await expect(
    page.getByTestId("document-ready").getByText("notes.txt"),
  ).toBeVisible();

  // Close the modal — the Esc key dismisses it cleanly.
  await page.keyboard.press("Escape");

  // The active-doc banner is now anchored above the chat input.
  await expect(page.getByTestId("active-doc-banner")).toBeVisible();

  // Ask in chat — should route to /document, not /chat.
  await page.getByTestId("chat-input").fill("bu pdf ne hakkında");
  await page.getByTestId("send-button").click();

  await expect(
    page.getByText("Bu belge örnek bir kısa nottur ve test amaçlıdır."),
  ).toBeVisible();

  // Dismissing the banner returns to general chat.
  await page.getByTestId("clear-active-doc").click();
  await expect(page.getByTestId("active-doc-banner")).toHaveCount(0);
});
