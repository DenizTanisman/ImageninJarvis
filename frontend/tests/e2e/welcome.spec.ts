import { expect, test } from "@playwright/test";

/**
 * Scenario 1 — Welcome flow.
 * Cold load → home → both navigation paths → chat shows the greeting.
 */
test("home loads and routes to chat + voice", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByTestId("nav-chat")).toBeVisible();
  await expect(page.getByTestId("nav-voice")).toBeVisible();

  await page.getByTestId("nav-chat").click();
  await expect(page).toHaveURL(/\/chat$/);

  // The conversation store seeds a greeting message.
  await expect(page.getByText("Merhaba, size nasıl yardımcı olabilirim?")).toBeVisible();

  // ShortcutBar persists across the chat surface.
  await expect(page.getByTestId("shortcut-mail")).toBeVisible();
  await expect(page.getByTestId("shortcut-calendar")).toBeVisible();
  await expect(page.getByTestId("shortcut-document")).toBeVisible();
  await expect(page.getByTestId("shortcut-translation")).toBeVisible();

  // Back home and into voice — confirms both navigations from a single load.
  await page.getByTestId("back-home").click();
  await expect(page).toHaveURL(/\/$/);
  await page.getByTestId("nav-voice").click();
  await expect(page).toHaveURL(/\/voice$/);
});
