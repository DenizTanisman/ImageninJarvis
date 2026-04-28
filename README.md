# Jarvis — Mode-Agnostic AI Assistant

A personal AI assistant that switches seamlessly between **voice and chat** while sharing the same conversation state and the same set of pluggable capabilities. Capabilities are wired through a Strategy + Registry pattern, so adding a new one — say a Slack summarizer — means dropping a single file in `capabilities/` and registering it. No core code changes.

## What it does

- **Mode-agnostic conversation:** speak in voice mode, switch to chat, keep the same history. STT/TTS run in the browser (Web Speech API); the backend never sees audio.
- **Gmail (read-only + send):** classified inbox summary across 4 buckets (important / DM / promo / other), 24-hour SQLite cache, batch-reply flow with per-mail confirmation.
- **Translation:** Gemini-backed translation between 7 languages with auto source-language detection.
- **Calendar CRUD:** chat-driven create ("yarın 14'te toplantı ekle") and delete ("X'i sil" → confirmation card), inline edit/delete cards in the chat history, ambiguity resolved via candidate list.
- **Document Q&A:** PDF / TXT upload (≤ 10 MB) or Drive picker → chunked, sandboxed, queryable. The active document follows you across screens via a context store, so questions asked in chat or voice route automatically to the document pipeline.

## Tech stack

| Layer | Tech | Notes |
|---|---|---|
| Frontend | React 18 + Vite + TypeScript | shadcn/ui + Tailwind |
| State | Zustand | conversation / mail / document context |
| STT/TTS | Web Speech API | browser-native, no backend audio |
| Backend | FastAPI + Python 3.11 | async, dependency-injected |
| LLM | Gemini 2.5 Flash | classifier + content generation |
| Auth | google-auth-oauthlib | one consent screen for Gmail + Calendar + Drive |
| Storage | SQLite | OAuth tokens (Fernet-encrypted), 24h email cache |
| Tests | pytest + vitest | 299 backend, 83 frontend |

## Architecture

```
User text/voice
       │
       ▼
   Classifier (Gemini)
       │  → {type: mail|translation|calendar|document|fallback, payload}
       ▼
   Dispatcher
       │  ↓ Registry.find(intent)
       ▼
   CapabilityStrategy.execute(payload) → Result(Success | Error)
       │
       ▼
   Frontend
   ├─ chat:   inline rich card (MailCard / CalendarEventCard / EventList / …)
   └─ voice:  TTS speaks meta.voice_summary; chat history still gets the rich payload
```

Every capability implements the same `CapabilityStrategy` interface (`can_handle`, `execute`, `render_hint`). The `Result` type forces graceful failure modes — strategies never raise; they return `Error(user_message=..., user_notify=...)` so the UI always has a sanitized message to show.

UML diagrams live in `docs/UML/`.

## Features

- [x] Voice ↔ Chat mode with preserved state, barge-in (TTS auto-cancels when the user starts speaking), no-speech recovery prompts
- [x] Gmail summary with 4-category classification + 24h cache
- [x] Gmail batch reply — per-mail draft preview + explicit confirmation before send
- [x] Translation (TR/EN/DE/FR/ES/RU/AR) with auto source detection
- [x] Calendar CRUD: create/list from chat, full edit + delete via inline cards, chat-driven delete with confirmation
- [x] Document Q&A across PDF + TXT, Drive picker, sandboxed temp storage with 24h sweep
- [x] Inline rich rendering in chat — capability results render as the actual UI component, not as text
- [x] Active-document banner: questions auto-route to document Q&A until dismissed

## Setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # fill in GEMINI_API_KEY, Google OAuth IDs, ENCRYPTION_KEY
uvicorn app.main:app --reload --port 8000
```

`ENCRYPTION_KEY` must be a 32-byte urlsafe base64 string — generate with:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env       # VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

### Tests

```bash
cd backend && pytest                 # 299 tests
cd frontend && npm run test -- --run # 83 tests
cd frontend && npm run build         # type-check + production bundle
```

## Security

- **Secrets:** every credential lives in `.env` (gitignored). `python-dotenv` loads at startup; nothing is hardcoded.
- **OAuth scopes — least privilege:** Gmail readonly + send, Calendar events, Drive readonly. Tokens stored in SQLite under a Fernet-encrypted column.
- **Prompt injection defense:** user input is wrapped in `<user_content>...</user_content>` tags before reaching the classifier; the system prompt instructs the model to treat that region as data, not as instructions.
- **Upload sandbox:** PDF/TXT only (validated by reading the binary, not by extension), 10 MB cap, files written to `/tmp/jarvis_sandbox/<uuid>/` and deleted in a `try/finally`. Hourly background sweep removes any stragglers older than 24 h.
- **Destructive actions require confirmation:** Gmail send, calendar delete, and chat-driven delete-by-name all surface a card; nothing is sent or deleted without an explicit click.
- **CORS:** whitelist-only (no wildcards).
- **Rate limiting:** `slowapi` on public routes (`/upload` 10/min, etc.).

## Roadmap

- [ ] Document RAG — swap the naive "first 3 chunks" retrieval for embedding-based search
- [ ] Multi-user — token store per user, row-level isolation
- [ ] Mobile (React Native or PWA)
- [ ] Mail compose from chat ("X@example.com'a Y konusunda mail at" → editable draft card)
- [ ] Voice batch reply — multi-turn TTS confirmation for sending mails by voice

## Repo layout

```
backend/
  app/          FastAPI routes + dependencies
  capabilities/ gmail, translation, calendar, document — each is a Strategy
  core/         dispatcher, classifier, base_strategy, result type, voice_formatter
  services/     gemini_client, auth_oauth, document_store, cache_sqlite
  tests/        unit + integration

frontend/
  src/
    screens/      HomeScreen, ChatScreen, VoiceScreen
    components/   MessageBubble, ShortcutBar, capability/*
    store/        zustand stores (conversation, mail, document, mode)
    api/          typed client for /chat, /mail/*, /calendar, /document, /upload, /drive/*
    hooks/        useSpeechRecognition, useSpeechSynthesis

docs/UML/       architecture diagrams
```

## License

MIT.
