# Jarvis frontend

Vite + React 18 + TypeScript + Tailwind + shadcn/ui. See the root [README](../README.md) for the full project overview.

## Run

```bash
npm install
cp .env.example .env       # VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

App at `http://localhost:5173`. Backend must be running at `VITE_API_BASE_URL` for capabilities to work; the UI degrades gracefully if not.

## Scripts

```bash
npm run dev               # vite dev server, HMR
npm run build             # tsc -b + vite build → dist/
npm run preview           # serve dist/
npm run test -- --run     # vitest, single run
npm run lint              # eslint
```

## Layout

```
src/
  screens/      HomeScreen, ChatScreen, VoiceScreen
  components/
    BotAvatar, ChatInput, MessageBubble, ShortcutBar
    capability/
      MailCard, MailRangeSelector, BatchReplyView
      TranslationCard
      CalendarForm, EventList, CalendarEventCard
      DocumentCard
      CapabilityModal              shared shell that opens any capability's modal UI
  store/
    conversation                   chat history + addMessage(role, text, payload?)
    mail                           range state for the mail shortcut
    document                       active uploaded doc — drives auto-routing in chat / voice
    mode                           active surface (voice / chat)
  api/
    client                         typed fetch wrappers for every backend route
  hooks/
    useSpeechRecognition           wraps SpeechRecognition with start/stop/interim
    useSpeechSynthesis             wraps SpeechSynthesis with cancel + isSpeaking
  test/                            vitest specs
```

## Rich rendering pattern

When the backend dispatcher returns `Success(ui_type, data, meta)`, the chat doesn't stringify the payload — it stores both the headline text (`meta.voice_summary`) and the raw payload on the `ChatMessage` object. `MessageBubble` then dispatches on `payload.ui_type`:

| `ui_type` | Component rendered inline |
|---|---|
| `MailCard` | `<MailCard initialData hideRangeSelector />` |
| `CalendarEvent` | `<CalendarEventCard event action={meta.action} />` |
| `EventList` | `<EventList initialEvents headline />` |
| `TranslationCard` / others | text bubble (no rich variant yet) |

Voice surface speaks `meta.voice_summary` and *also* writes the same payload to the conversation store, so switching to chat afterwards reveals the actual card.

## Speech APIs

- `useSpeechRecognition` exposes `{transcript, interimTranscript, isListening, isSupported, error, start, stop, reset}`.
- `useSpeechSynthesis` exposes `{speak, cancel, isSpeaking}`.
- Barge-in: `VoiceScreen` watches `interimTranscript` and calls `synth.cancel()` on the first token, so the assistant stops talking the moment the user opens their mouth.
- No-speech recovery: when STT emits `no-speech`, we toast *and* speak "anlayamadım, tekrarlar mısın?" so a voice-only user gets a voice answer.

## Tests

83 vitest specs covering each screen + each capability card + the API client + the stores + persistence. Mocks live alongside each test file; no network is hit.

```bash
npm run test -- --run               # all
npm run test -- --run ChatScreen    # filter by name
```
