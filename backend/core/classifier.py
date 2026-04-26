"""Intent classifier.

Maps a free-form user message to an :class:`Intent`. Constructed with no
arguments → returns ``fallback`` for everything (legacy stub behavior).
Constructed with a :class:`GeminiClient` → asks the model to pick from
the supported intent types and falls back gracefully on any parsing or
network error so the dispatcher always gets a usable Intent.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

from services.gemini_client import GeminiClient, GeminiUnavailable

from .classifier_prompts import (
    CLASSIFIER_SYSTEM_PROMPT,
    build_classifier_user_message,
)

logger = logging.getLogger(__name__)

IntentType = Literal["fallback", "mail", "translation", "calendar", "document"]
SUPPORTED_INTENT_TYPES: tuple[IntentType, ...] = (
    "fallback",
    "translation",
)


@dataclass(frozen=True)
class Intent:
    type: IntentType
    text: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "text": self.text, "payload": dict(self.payload)}


class Classifier:
    """Maps a free-form user utterance to an :class:`Intent`."""

    def __init__(self, gemini: GeminiClient | None = None) -> None:
        self._gemini = gemini

    async def classify(self, text: str) -> Intent:
        cleaned = text.strip()
        if not cleaned or self._gemini is None:
            return Intent(type="fallback", text=cleaned, payload={})

        prompt = build_classifier_user_message(cleaned)
        try:
            raw = await self._gemini.generate_json(
                prompt, system=CLASSIFIER_SYSTEM_PROMPT
            )
        except (GeminiUnavailable, ValueError) as exc:
            logger.info("Classifier falling back (Gemini error): %s", exc)
            return Intent(type="fallback", text=cleaned, payload={})

        return _coerce_intent(raw, cleaned)


def _coerce_intent(raw: object, cleaned_text: str) -> Intent:
    if not isinstance(raw, dict):
        return Intent(type="fallback", text=cleaned_text, payload={})

    intent_type = raw.get("type")
    if intent_type not in SUPPORTED_INTENT_TYPES:
        return Intent(type="fallback", text=cleaned_text, payload={})

    payload = raw.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {}

    if intent_type == "translation" and not _valid_translation_payload(payload):
        logger.info("Translation intent missing required payload, falling back.")
        return Intent(type="fallback", text=cleaned_text, payload={})

    return Intent(type=intent_type, text=cleaned_text, payload=payload)  # type: ignore[arg-type]


def _valid_translation_payload(payload: dict[str, Any]) -> bool:
    text = payload.get("text")
    target = payload.get("target")
    return isinstance(text, str) and bool(text.strip()) and isinstance(target, str) and bool(target.strip())
