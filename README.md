# Jarvis — Personal AI Assistant

Mode-agnostic (voice ↔ chat) personal assistant with pluggable capabilities: Gmail summary + batch reply, translation, calendar CRUD, document Q&A.

> **Status:** In development. See `CLAUDE.md` for the step-by-step roadmap.

## Repo layout

```
backend/    FastAPI + Gemini + capability strategies
frontend/   Vite + React + TypeScript + Tailwind + shadcn/ui
docs/       UML and architecture notes
```

## Local development

### Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in real values
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Security & privacy

See `CLAUDE.md` §4 (security protocol) and §5 (privacy). Secrets live in `.env` (gitignored). Never commit real credentials.
