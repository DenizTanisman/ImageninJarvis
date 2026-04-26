const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface ChatErrorPayload {
  user_message: string;
  retry_after?: number | null;
}

export interface ChatSuccessResponse {
  ok: true;
  ui_type: string;
  data: unknown;
  meta?: Record<string, unknown> | null;
}

export interface ChatErrorResponse {
  ok: false;
  error: ChatErrorPayload;
}

export type ChatResponse = ChatSuccessResponse | ChatErrorResponse;

export class ChatNetworkError extends Error {
  constructor(message: string, readonly cause?: unknown) {
    super(message);
    this.name = "ChatNetworkError";
  }
}

export async function sendChat(text: string, signal?: AbortSignal): Promise<ChatResponse> {
  return postJson<ChatResponse>("/chat", { text }, signal);
}

export interface MailEntry {
  id: string;
  from: string;
  subject: string;
  snippet: string;
  summary: string;
  needs_reply: boolean;
  confidence: number;
  thread_id?: string;
}

export interface MailSummaryData {
  range: { kind: "daily" | "weekly" | "custom"; after: string; before: string };
  categories: {
    important: MailEntry[];
    dm: MailEntry[];
    promo: MailEntry[];
    other: MailEntry[];
  };
  needs_reply_count: number;
  total: number;
}

export type MailSummaryResponse =
  | { ok: true; ui_type: string; data: MailSummaryData; meta?: Record<string, unknown> | null }
  | ChatErrorResponse;

export async function fetchMailSummary(
  body: { range_kind: "daily" | "weekly" | "custom"; after: string; before: string; max_results?: number },
  signal?: AbortSignal,
): Promise<MailSummaryResponse> {
  return postJson<MailSummaryResponse>("/mail/summary", body, signal);
}

export interface AuthStatus {
  connected: boolean;
  scopes: string[];
  can_send: boolean;
}

export interface ReplyDraftDTO {
  message_id: string;
  thread_id: string;
  to: string;
  subject: string;
  body: string;
}

export interface DraftsResponseDTO {
  drafts: ReplyDraftDTO[];
  failures: string[];
}

export async function generateDrafts(
  message_ids: string[],
  signal?: AbortSignal,
): Promise<DraftsResponseDTO> {
  return postJson<DraftsResponseDTO>("/mail/drafts", { message_ids }, signal);
}

export interface SendDraftRequest extends ReplyDraftDTO {}

export interface SendDraftResponse {
  sent_message_id: string | null;
  error: ChatErrorPayload | null;
}

export async function sendDraft(
  draft: SendDraftRequest,
  signal?: AbortSignal,
): Promise<SendDraftResponse> {
  return postJson<SendDraftResponse>("/mail/send", draft, signal);
}

export async function getAuthStatus(signal?: AbortSignal): Promise<AuthStatus> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/mail/auth-status`, { signal });
  } catch (err) {
    throw new ChatNetworkError("Backend'e ulaşılamadı.", err);
  }
  if (!response.ok) {
    throw new ChatNetworkError(`Sunucu hatası (HTTP ${response.status}).`);
  }
  return (await response.json()) as AuthStatus;
}

export function googleConnectUrl(): string {
  return `${API_BASE_URL}/auth/google/start`;
}

async function postJson<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    throw new ChatNetworkError("Backend'e ulaşılamadı.", err);
  }

  if (!response.ok && response.status !== 200) {
    let parsed: unknown = null;
    try {
      parsed = await response.json();
    } catch {
      // body parse failure is non-fatal here
    }
    throw new ChatNetworkError(
      `Sunucu hatası (HTTP ${response.status}).`,
      parsed,
    );
  }

  return (await response.json()) as T;
}
