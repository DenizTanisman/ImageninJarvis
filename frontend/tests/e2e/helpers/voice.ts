import type { Page } from "@playwright/test";

/**
 * Web Speech API isn't headless-friendly — Chromium ships the surface
 * but won't actually capture audio in tests. We stub the two browser
 * globals before the app loads so `useSpeechRecognition` /
 * `useSpeechSynthesis` think the platform is supported, and we expose
 * a tiny test-only bridge under `window.__voiceTest` to drive
 * recognition events from the spec.
 */
export async function installSpeechStubs(page: Page) {
  await page.addInitScript(() => {
    // ---- SpeechRecognition stub ----
    interface FakeRecognition extends EventTarget {
      continuous: boolean;
      interimResults: boolean;
      lang: string;
      start: () => void;
      stop: () => void;
      abort: () => void;
      onresult: ((e: unknown) => void) | null;
      onerror: ((e: unknown) => void) | null;
      onstart: (() => void) | null;
      onend: (() => void) | null;
    }

    const recognitions: FakeRecognition[] = [];

    class StubSpeechRecognition extends EventTarget implements FakeRecognition {
      continuous = false;
      interimResults = true;
      lang = "tr-TR";
      onresult: ((e: unknown) => void) | null = null;
      onerror: ((e: unknown) => void) | null = null;
      onstart: (() => void) | null = null;
      onend: (() => void) | null = null;

      constructor() {
        super();
        recognitions.push(this);
      }
      start() {
        this.onstart?.();
      }
      stop() {
        this.onend?.();
      }
      abort() {
        this.onend?.();
      }
    }

    (window as unknown as { SpeechRecognition: unknown }).SpeechRecognition =
      StubSpeechRecognition;
    (
      window as unknown as { webkitSpeechRecognition: unknown }
    ).webkitSpeechRecognition = StubSpeechRecognition;

    // ---- SpeechSynthesis stub ----
    const spoken: string[] = [];
    const synth = {
      speaking: false,
      paused: false,
      pending: false,
      speak(utt: { text: string; onend?: () => void }) {
        spoken.push(utt.text);
        synth.speaking = true;
        // Resolve "done" on next tick so isSpeaking flips back.
        setTimeout(() => {
          synth.speaking = false;
          utt.onend?.();
        }, 0);
      },
      cancel() {
        synth.speaking = false;
      },
      getVoices: () => [],
      addEventListener: () => {},
      removeEventListener: () => {},
    };
    Object.defineProperty(window, "speechSynthesis", {
      value: synth,
      configurable: true,
    });
    class StubUtterance {
      text: string;
      onend: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor(text: string) {
        this.text = text;
      }
    }
    (window as unknown as { SpeechSynthesisUtterance: unknown }).SpeechSynthesisUtterance =
      StubUtterance;

    // ---- test bridge ----
    (window as unknown as { __voiceTest: unknown }).__voiceTest = {
      /**
       * Fire a final-transcript result followed by recognition end —
       * the hook only invokes its `onFinal` callback in the onend
       * handler, so we have to drive both events to mimic real STT.
       */
      emitFinal(text: string) {
        const r = recognitions[recognitions.length - 1];
        if (!r) return;
        const event = {
          results: [
            {
              0: { transcript: text },
              isFinal: true,
              length: 1,
            },
          ],
          resultIndex: 0,
        };
        r.onresult?.(event);
        r.onend?.();
      },
      ready: () => recognitions.length > 0,
      spoken,
    };
  });
}

/** Drive a final-transcript event from the spec. Waits until VoiceScreen
 * has mounted its recognition instance before firing — VoiceScreen
 * starts the mic in a useEffect, so a too-eager call would no-op. */
export async function speak(page: Page, text: string) {
  await page.waitForFunction(() =>
    (
      window as unknown as {
        __voiceTest?: { ready: () => boolean };
      }
    ).__voiceTest?.ready(),
  );
  await page.evaluate((t) => {
    (
      window as unknown as { __voiceTest: { emitFinal: (s: string) => void } }
    ).__voiceTest.emitFinal(t);
  }, text);
}
