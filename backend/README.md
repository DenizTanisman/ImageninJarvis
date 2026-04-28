# Jarvis backend

FastAPI + Gemini + Strategy/Registry capability dispatch. See the root [README](../README.md) for the full project overview.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # fill values
uvicorn app.main:app --reload --port 8000
```

`/health` should return `{"status": "ok"}` once the server is up.

## Required env

| Key | Notes |
|---|---|
| `GEMINI_API_KEY` | from [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth web client; redirect URI must match `GOOGLE_REDIRECT_URI` exactly |
| `GOOGLE_REDIRECT_URI` | default `http://localhost:8000/auth/google/callback` |
| `ENCRYPTION_KEY` | 32-byte urlsafe base64 — `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `CORS_ORIGINS` | comma-separated whitelist; no `*` |
| `DATABASE_URL` | SQLite path — default `sqlite:///./jarvis.db` |
| `GEMINI_MODEL` | optional override; default `gemini-2.5-flash` |

`.env` is gitignored. Never commit real values.

## Layout

```
app/          FastAPI entry + routes (chat, voice, mail, calendar, document, upload, drive, auth)
core/         dispatcher, classifier, base_strategy, result, voice_formatter, registry
capabilities/
  gmail/      strategy + adapter + classifier prompts + draft generator
  translation/
  calendar/
  document/   strategy + parser + chunker
services/     gemini_client, auth_oauth, document_store, cache_sqlite, secrets
tests/
  unit/       per-strategy + per-service unit tests with mocks
  integration/route-level tests with FastAPI TestClient
  security/   sandbox cleanup, upload validation
```

## Tests

```bash
pytest                                  # all tests (~5s)
pytest tests/unit/test_calendar_strategy.py -v
pytest -k delete                        # quick filter
ruff check                              # lint
```

299 tests as of this commit. Backend tests mock Gemini and Google APIs end-to-end — no network or real OAuth needed.

## Adding a capability

1. New folder `capabilities/<name>/` with `strategy.py`, `prompts.py`, `models.py`, `adapter.py` (if external API).
2. Subclass `CapabilityStrategy` from `core/base_strategy.py`. Implement `can_handle(intent)`, `execute(payload)` returning `Success | Error`. Set `name`, `intent_keys`, `render_hint()`.
3. Register the strategy in `app/dependencies.py` (or wherever the project wires the registry).
4. Add an intent example to `core/classifier_prompts.py` so the classifier learns the new intent type.
5. Drop a unit test under `tests/unit/test_<name>_strategy.py` mocking the adapter.

No existing code changes. Open/Closed by design.

## Security guardrails

Enforced in code, not just docs:

- All user input enters Gemini wrapped in `<user_content>...</user_content>` with a system-prompt instruction to treat that span as data, not instructions (`core/classifier_prompts.py`).
- OAuth tokens are encrypted at rest (`services/auth_oauth.py` + `cryptography.fernet`).
- Upload validation reads the binary header — extension is never trusted (`app/routes/upload.py`).
- Sandbox cleanup is `try/finally` per request *plus* an hourly background sweep over 24h+ stale folders (`services/document_store.py`).
- Destructive routes (`/mail/send`, `/calendar` delete) require an explicit body — there is no implicit "send all drafts" or "delete all" endpoint.
