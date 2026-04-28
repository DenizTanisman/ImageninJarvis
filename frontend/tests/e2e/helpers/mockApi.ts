import type { Page, Route } from "@playwright/test";

/**
 * Helpers that intercept backend calls so each E2E spec runs without a
 * live backend, Gemini, or Google. Tests opt into the routes they need
 * via `mock.<area>(page, ...)`. Anything not explicitly stubbed will
 * fall through to the real network — which means a CI failure rather
 * than a silent flake against a live API.
 */

/** All mock routes anchor on `localhost:8000` so they don't fight with
 * the vite dev server's SPA fallback (e.g. `goto("/chat")` would
 * otherwise be intercepted by a `/chat` API mock and rendered as raw
 * JSON instead of the page). */
const API = "http://localhost:8000";
const json = (route: Route, body: unknown, status = 200) =>
  route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });

export const mock = {
  /** Pretend Google is connected with all required scopes. */
  async authConnected(page: Page) {
    await page.route(`${API}/mail/auth-status`, (route) =>
      json(route, {
        connected: true,
        scopes: [
          "https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.send",
          "https://www.googleapis.com/auth/calendar.events",
          "https://www.googleapis.com/auth/drive.readonly",
        ],
        can_send: true,
        can_calendar: true,
        can_drive: true,
      }),
    );
  },

  /** Stub /chat — `responder` decides what the dispatcher returns. */
  async chat(
    page: Page,
    responder: (text: string) => {
      ui_type: string;
      data: unknown;
      meta?: Record<string, unknown>;
    },
  ) {
    await page.route(`${API}/chat`, async (route) => {
      const body = JSON.parse(route.request().postData() ?? "{}") as {
        text: string;
      };
      const out = responder(body.text ?? "");
      await json(route, {
        ok: true,
        ui_type: out.ui_type,
        data: out.data,
        meta: { voice_summary: "", ...(out.meta ?? {}) },
      });
    });
  },

  async mailSummary(page: Page, data: unknown) {
    await page.route(`${API}/mail/summary`, (route) =>
      json(route, {
        ok: true,
        ui_type: "MailCard",
        data,
        meta: { source: "live" },
      }),
    );
  },

  async drafts(
    page: Page,
    drafts: Array<{
      message_id: string;
      thread_id: string;
      to: string;
      subject: string;
      body: string;
    }>,
  ) {
    await page.route(`${API}/mail/drafts`, (route) =>
      json(route, { drafts, failures: [] }),
    );
  },

  async sendDraft(page: Page) {
    await page.route(`${API}/mail/send`, (route) =>
      json(route, { sent_message_id: "sent-1", error: null }),
    );
  },

  async sendNewMail(page: Page) {
    await page.route(`${API}/mail/send-new`, (route) =>
      json(route, { sent_message_id: "sent-new-1", error: null }),
    );
  },

  async calendar(
    page: Page,
    responder: (
      action: string,
      payload: Record<string, unknown>,
    ) =>
      | {
          ok: true;
          ui_type: string;
          data: unknown;
          meta?: Record<string, unknown>;
        }
      | { ok: false; error: { user_message: string } },
  ) {
    await page.route(`${API}/calendar`, async (route) => {
      const body = JSON.parse(route.request().postData() ?? "{}");
      const action = String(body.action ?? "");
      await json(route, responder(action, body));
    });
  },

  async upload(
    page: Page,
    doc: {
      doc_id: string;
      page_count: number;
      original_name: string;
      mime_type: string;
      size_bytes: number;
    },
  ) {
    await page.route(`${API}/upload`, (route) => json(route, doc));
  },

  async documentAsk(
    page: Page,
    answerer: (question: string, doc_id: string) => string,
  ) {
    await page.route(`${API}/document`, async (route) => {
      const body = JSON.parse(route.request().postData() ?? "{}") as {
        doc_id: string;
        question: string;
      };
      await json(route, {
        ok: true,
        ui_type: "DocumentAnswer",
        data: {
          doc_id: body.doc_id,
          question: body.question,
          answer: answerer(body.question, body.doc_id),
          chunks_used: 1,
          total_chunks: 1,
        },
        meta: {},
      });
    });
  },
};

export { API };
