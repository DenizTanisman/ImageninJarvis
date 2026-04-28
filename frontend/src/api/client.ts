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

export interface MailDraftCardData {
  to: string;
  subject: string;
  body: string;
  instruction?: string;
}

export interface SendNewRequest {
  to: string;
  subject: string;
  body: string;
}

export async function sendNewMail(
  body: SendNewRequest,
  signal?: AbortSignal,
): Promise<SendDraftResponse> {
  return postJson<SendDraftResponse>("/mail/send-new", body, signal);
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

export interface TranslationData {
  source_text: string;
  translated_text: string;
  source_lang: string;
  target_lang: string;
}

export type TranslationResponse =
  | { ok: true; ui_type: string; data: TranslationData; meta?: Record<string, unknown> | null }
  | ChatErrorResponse;

export async function translate(
  body: { text: string; source: string; target: string },
  signal?: AbortSignal,
): Promise<TranslationResponse> {
  return postJson<TranslationResponse>("/translation", body, signal);
}

export interface CalendarEventDTO {
  id: string;
  summary: string;
  start: string;
  end: string;
  description: string;
  html_link: string;
}

export interface CalendarListData {
  events: CalendarEventDTO[];
  days: number;
}

export type CalendarResponse =
  | { ok: true; ui_type: "EventList"; data: CalendarListData; meta?: Record<string, unknown> | null }
  | { ok: true; ui_type: "CalendarEvent"; data: CalendarEventDTO; meta?: { action: "create" | "update" } | null }
  | { ok: true; ui_type: "text"; data: { event_id: string }; meta?: { action: "delete" } | null }
  | ChatErrorResponse;

export interface CalendarCreatePayload {
  action: "create";
  summary: string;
  start: string;
  end: string;
  description?: string;
}

export interface CalendarUpdatePayload {
  action: "update";
  event_id: string;
  summary?: string;
  start?: string;
  end?: string;
  description?: string;
}

export interface CalendarDeletePayload {
  action: "delete";
  event_id: string;
}

export interface CalendarListPayload {
  action: "list";
  days?: number;
}

type CalendarPayload =
  | CalendarListPayload
  | CalendarCreatePayload
  | CalendarUpdatePayload
  | CalendarDeletePayload;

export async function callCalendar(
  body: CalendarPayload,
  signal?: AbortSignal,
): Promise<CalendarResponse> {
  return postJson<CalendarResponse>("/calendar", body, signal);
}

export interface UploadedDocDTO {
  doc_id: string;
  page_count: number;
  original_name: string;
  mime_type: string;
  size_bytes: number;
}

export async function uploadDocument(
  file: File,
  signal?: AbortSignal,
): Promise<UploadedDocDTO> {
  const form = new FormData();
  form.append("file", file);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/upload`, {
      method: "POST",
      body: form,
      signal,
    });
  } catch (err) {
    throw new ChatNetworkError("Backend'e ulaşılamadı.", err);
  }
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new ChatNetworkError(detail);
  }
  return (await response.json()) as UploadedDocDTO;
}

export interface DriveFileDTO {
  id: string;
  name: string;
  mime_type: string;
  size_bytes: number;
  modified_time: string;
}

export async function listDriveFiles(signal?: AbortSignal): Promise<DriveFileDTO[]> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/drive/files`, { signal });
  } catch (err) {
    throw new ChatNetworkError("Backend'e ulaşılamadı.", err);
  }
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw new ChatNetworkError("Drive'a bağlı değilsin ya da Drive iznini vermemişsin.");
    }
    throw new ChatNetworkError(`Drive listesi alınamadı (HTTP ${response.status}).`);
  }
  const body = (await response.json()) as { files: DriveFileDTO[] };
  return body.files;
}

export async function importDriveFile(
  fileId: string,
  signal?: AbortSignal,
): Promise<UploadedDocDTO> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/drive/import`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ file_id: fileId }),
      signal,
    });
  } catch (err) {
    throw new ChatNetworkError("Backend'e ulaşılamadı.", err);
  }
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new ChatNetworkError(detail);
  }
  return (await response.json()) as UploadedDocDTO;
}

export interface DocumentAnswerDTO {
  doc_id: string;
  question: string;
  answer: string;
  chunks_used: number;
  total_chunks: number;
}

export type DocumentAskResponse =
  | { ok: true; ui_type: "DocumentAnswer"; data: DocumentAnswerDTO; meta?: Record<string, unknown> | null }
  | ChatErrorResponse;

export async function askDocument(
  body: { doc_id: string; question: string },
  signal?: AbortSignal,
): Promise<DocumentAskResponse> {
  return postJson<DocumentAskResponse>(
    "/document",
    { action: "ask", ...body },
    signal,
  );
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
