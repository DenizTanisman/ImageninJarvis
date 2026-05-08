# Jarvis — Mode-Agnostic AI Assistant

A personal assistant that talks the same way whether you type or speak. Switch from chat to voice mid-conversation and the history travels with you. Capabilities (Gmail, Calendar, Translation, Documents, Journal) are pluggable — adding a new one means dropping a file in `capabilities/` and registering it.

> **Language:** Jarvis replies in English regardless of the input language. Type Turkish, get English back — the translation capability is the only place where output language is user-controlled (you pick the target).

---

## What it does

- **Mode-agnostic conversation.** Speak in voice mode, switch to chat, history is preserved. STT/TTS run in the browser via the Web Speech API — no audio leaves your machine.
- **Gmail summary + send.** Inbox classified into Important / DM / Promo / Other; 24-hour SQLite cache; batch-reply with per-mail confirmation; chat-driven compose ("send a mail to X about Y" → editable draft → send).
- **Translation.** TR / EN / DE / FR / ES / RU / AR with auto source detection.
- **Calendar CRUD.** Create from chat ("schedule a meeting tomorrow at 2pm"), list upcoming events, edit/delete via inline cards. Destructive actions always need a confirmation click.
- **Document Q&A.** Upload PDF/TXT (≤ 10 MB) or pick from Drive. Once active, every chat or voice question routes to the document until you dismiss the banner.
- **Journal reports** *(optional, requires external Journal AI Reporter)*. Quickbar shortcuts (`/detail`, `/todo`, `/concern`, `/success`, `/date{dd.mm.yyyy}`) generate markdown reports from a journal backend.

---

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | React 18 · Vite · TypeScript · Tailwind · shadcn/ui |
| State | Zustand |
| STT/TTS | Web Speech API (browser-native, no audio sent to backend) |
| Backend | FastAPI · Python 3.11+ · async, dependency-injected |
| LLM | Gemini 2.5 Flash (classifier + content generation) |
| Auth | google-auth-oauthlib (one consent for Gmail + Calendar + Drive) |
| Storage | SQLite (Fernet-encrypted OAuth tokens, 24h email cache) |
| Tests | pytest (335) · vitest (86) · Playwright (E2E) |

---

## Quickstart

You'll need: Python 3.11+, Node 20+, a [Gemini API key](https://aistudio.google.com/app/apikey), and a Google Cloud OAuth client (only if you want Gmail/Calendar/Drive — translation and chat work without it).

### 1. Clone

```bash
git clone https://github.com/DenizTanisman/ImageninJarvis.git
cd ImageninJarvis
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env`:

```bash
GEMINI_API_KEY=...                 # required
ENCRYPTION_KEY=...                 # see command below
GOOGLE_CLIENT_ID=...               # only for Gmail/Calendar/Drive
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

Generate `ENCRYPTION_KEY` (used to encrypt stored OAuth tokens):

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Start the API:

```bash
uvicorn app.main:app --reload --port 8000
# Verify: curl http://localhost:8000/health → {"status":"ok"}
```

### 3. Frontend

```bash
cd ../frontend
npm install
cp .env.example .env.local         # default points at http://localhost:8000
npm run dev
# Open http://localhost:5173
```

### 4. (Optional) Google OAuth setup

For Gmail / Calendar / Drive features:

1. [Google Cloud Console](https://console.cloud.google.com) → create a project → **APIs & Services** → enable Gmail, Calendar, Drive APIs.
2. **OAuth consent screen** → External, add your Google account as a test user.
3. **Credentials** → Create OAuth Client ID → Web application.
4. Authorized redirect URI: `http://localhost:8000/auth/google/callback`.
5. Copy Client ID + Secret into `backend/.env`.
6. In the app, click **Connect Google** when a capability prompts you.

Scopes requested (least-privilege): `gmail.readonly`, `gmail.send`, `calendar.events`, `drive.readonly`.

---

## How to use

| Where | What to do |
|---|---|
| Home screen | Click 🎤 for voice or 💬 for chat |
| Chat — type freely | "summarize today's emails", "translate this to Russian: hello", "schedule lunch tomorrow at noon" |
| Chat — shortcut bar (top) | Mail / Translate / Calendar / Document — opens a focused modal |
| Chat — journal quickbar (bottom) | One-tap `/detail`, `/todo`, `/concern`, `/success` (requires Reporter URL) |
| Voice | Mic auto-starts. Speak naturally; barge-in cuts the assistant when you start talking. The voice surface speaks a short summary and the chat history still gets the full rich card |
| Document mode | Upload or pick a PDF/TXT → questions auto-route to the document until you click ✕ on the banner |
| Mail compose | Type "send a mail to alice@example.com about the Q2 deadline" → editable draft card → confirm → send (always asks before sending) |

---

## Run the tests

```bash
# Backend (335 tests)
cd backend && .venv/bin/pytest

# Frontend (86 vitest specs)
cd frontend && npm run test -- --run

# E2E (5 Playwright scenarios — uses system Chrome by default)
cd frontend && npm run test:e2e
# Run once if missing the bundled browser: npx playwright install chromium

# Type check + production build
cd frontend && npm run build
```

---

## Project layout

```
backend/
  app/
    main.py            FastAPI entry + middleware
    routes/            chat, mail, calendar, document, drive, upload, auth
    dependencies.py    DI wiring (singleton registry, oauth, gemini client)
    config.py          settings loaded from .env
  capabilities/        each is a self-contained Strategy
    gmail/             adapter, classifier, draft generator, prompts, strategy
    translation/
    calendar/
    document/
    journal/           (proxies external Journal Reporter; optional)
  core/
    classifier.py      Gemini intent parser
    dispatcher.py      routes intent → strategy → Result
    registry.py        capability lookup
    base_strategy.py   the contract every capability implements
    result.py          Success | Error union (no exceptions cross the boundary)
    voice_formatter.py rich payload → short TTS-friendly sentence
  services/
    gemini_client.py   retry + concurrency-limited wrapper
    auth_oauth.py      Google OAuth flow + Fernet token store
    document_store.py  in-memory chunk store with TTL sweep
    cache_sqlite.py    24h mail summary cache
  tests/               unit + integration

frontend/
  src/
    screens/           HomeScreen, ChatScreen, VoiceScreen
    components/
      capability/      MailCard, BatchReplyView, MailDraftCard,
                       CalendarForm, CalendarEventCard, EventList,
                       TranslationCard, DocumentCard, MailRangeSelector
      ChatInput, MessageBubble, ShortcutBar, JournalQuickbar, BotAvatar
    store/             zustand stores (conversation, mail, document, mode)
    api/client.ts      typed wrapper for every backend route
    hooks/             useSpeechRecognition, useSpeechSynthesis
  e2e/                 Playwright tests
docs/                  UML diagrams + per-tier READMEs
```

---

## Architecture

```
User text/voice
     │
     ▼
Classifier (Gemini)  →  {type: mail | translation | calendar | document | journal | fallback, payload}
     │
     ▼
Dispatcher
     │  Registry.find(intent) → CapabilityStrategy
     ▼
strategy.execute(payload) → Result(Success | Error)
     │
     ├─ chat:  inline rich card (MailCard, CalendarEventCard, EventList, …)
     └─ voice: TTS speaks `meta.voice_summary`; chat history still receives the full rich payload
```

Every capability implements:

```python
class CapabilityStrategy(ABC):
    name: str
    intent_keys: list[str]
    def can_handle(self, intent: dict) -> bool: ...
    async def execute(self, payload: dict) -> Result: ...   # never raises
    def render_hint(self) -> str: return "text"             # which UI component to render
```

Open/Closed in practice: adding a new capability touches one new folder + one line in `core/registry.py`. The dispatcher, the classifier, the chat surface, the voice surface — none of them change.

UML diagrams: [`docs/UML/`](docs/UML/).

---

## Security highlights

- **Secrets** in `.env` (gitignored); loaded via `python-dotenv`. No hardcoded credentials.
- **OAuth tokens** stored in SQLite under a Fernet-encrypted column.
- **Prompt injection defense:** user input is wrapped in `<user_content>...</user_content>` tags; system prompts instruct the model to treat that region as data.
- **Upload sandbox:** `.pdf` / `.txt` only (validated by reading the binary, not by extension), 10 MB cap, files written to `/tmp/jarvis_sandbox/<uuid>/` and deleted in `try/finally`. Hourly background sweep clears stragglers older than 24h.
- **Destructive actions need explicit confirmation** — Gmail send, calendar delete, chat-driven delete-by-name all surface a card; nothing fires without a click.
- **CORS** whitelist-only (no wildcards).
- **Rate limiting** via `slowapi` (e.g. `/upload` 10/min).
- **Errors never leak stack traces** to the client — `Error.user_message` is the only string shown.

---

## Roadmap

- [ ] Document RAG — replace the naive "first 3 chunks" retrieval with embedding-based search
- [ ] Multi-user — token store per user, row-level isolation
- [ ] Mobile (React Native or PWA)
- [ ] Voice batch reply — multi-turn TTS confirmation for sending mails by voice (Step 6.4, currently chat-only)

---

## License

MIT.
