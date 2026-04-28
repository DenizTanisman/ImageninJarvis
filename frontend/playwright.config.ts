import { defineConfig, devices } from "@playwright/test";

/**
 * Step 8.1 — E2E suite. We mock the backend at the network layer with
 * Playwright's `page.route` so the tests are deterministic and don't
 * require running uvicorn or hitting Gemini / Google. Backend already
 * has its own integration suite (FastAPI TestClient).
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "line" : "list",
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
  projects: [
    {
      // Uses the system Google Chrome rather than the bundled
      // playwright-chromium build — that binary is a 165 MB download
      // gated behind a slow CDN, and dev machines already ship with
      // Chrome. CI can switch to `name: "chromium"` (no `channel`)
      // after running `npx playwright install chromium`.
      name: "chrome",
      use: { ...devices["Desktop Chrome"], channel: "chrome" },
    },
  ],
});
