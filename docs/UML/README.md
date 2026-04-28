# UML diagrams

Architecture diagrams live in this folder. Drop the source PDF (e.g. `jarvis_uml_diagrams.pdf`) here and link to it from the root [README.md](../../README.md#architecture).

Suggested diagrams:

- **Class diagram** — `CapabilityStrategy` ABC, the four concrete strategies, `Result` union, `Registry`, `Dispatcher`, `Classifier`.
- **Sequence diagram (chat path)** — `User → ChatScreen → POST /chat → Dispatcher → Classifier → Strategy.execute → Result → MessageBubble (rich payload)`.
- **Sequence diagram (voice path)** — same as above plus the `voice_formatter` branch and barge-in cancellation of `SpeechSynthesis`.
- **Component diagram** — frontend Zustand stores (`conversation`, `mail`, `document`, `mode`) + backend services (`auth_oauth`, `gemini_client`, `document_store`, `cache_sqlite`).
- **Auth flow** — Google OAuth start → callback → encrypted token write → scope check on each request.
