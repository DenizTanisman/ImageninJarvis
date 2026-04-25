"""Intent classifier.

Step 1.3: stub that always returns a fallback intent. The dispatcher
treats fallback as "no capability matched, send to general LLM" later
in Step 1.4. Step 2+ wires this to Gemini for real intent parsing
(mail / translation / calendar / document) — the public surface
``classify(text)`` won't change.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

IntentType = Literal["fallback", "mail", "translation", "calendar", "document"]


@dataclass(frozen=True)
class Intent:
    type: IntentType
    text: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "text": self.text, "payload": dict(self.payload)}


class Classifier:
    """Maps a free-form user utterance to an :class:`Intent`."""

    async def classify(self, text: str) -> Intent:
        cleaned = text.strip()
        return Intent(type="fallback", text=cleaned, payload={})
