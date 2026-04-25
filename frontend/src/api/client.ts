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
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text }),
      signal,
    });
  } catch (err) {
    throw new ChatNetworkError("Backend'e ulaşılamadı.", err);
  }

  if (!response.ok && response.status !== 200) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // body parse failure is non-fatal here
    }
    throw new ChatNetworkError(
      `Sunucu hatası (HTTP ${response.status}).`,
      body,
    );
  }

  return (await response.json()) as ChatResponse;
}
