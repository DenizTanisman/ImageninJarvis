"""TranslationStrategy — stateless Gemini-backed translation.

No adapter, no cache: each call hits Gemini directly. The strategy
validates inputs, runs the prompt, and wraps the response (or any
GeminiUnavailable) into a Result so the dispatcher / route layer never
sees an exception.
"""
from __future__ import annotations

import logging
from typing import Any

from core.base_strategy import CapabilityStrategy
from core.result import Error, Result, Success
from services.gemini_client import GeminiClient, GeminiUnavailable

from .prompts import TRANSLATION_SYSTEM_PROMPT, build_translation_user_message

logger = logging.getLogger(__name__)

MAX_INPUT_CHARS = 8000
SUPPORTED_LANGS: tuple[str, ...] = (
    "auto",
    "tr",
    "en",
    "de",
    "fr",
    "es",
    "ru",
    "ar",
)


class TranslationStrategy(CapabilityStrategy):
    name = "translation"
    intent_keys = ("translate", "translation", "çevir", "çeviri")

    def __init__(self, gemini: GeminiClient) -> None:
        self._gemini = gemini

    def can_handle(self, intent: dict[str, Any]) -> bool:
        return intent.get("type") == "translation"

    async def execute(self, payload: dict[str, Any]) -> Result:
        text = (payload.get("text") or "").strip()
        source = (payload.get("source") or "auto").strip().lower()
        target = (payload.get("target") or "").strip().lower()

        if not text:
            return Error(
                message="empty text",
                user_message="Çevrilecek metin boş.",
                user_notify=True,
                log_level="info",
            )
        if len(text) > MAX_INPUT_CHARS:
            return Error(
                message=f"text exceeds {MAX_INPUT_CHARS} chars ({len(text)})",
                user_message=(
                    f"Metin çok uzun (en fazla {MAX_INPUT_CHARS} karakter)."
                ),
                user_notify=True,
                log_level="info",
            )
        if not target:
            return Error(
                message="missing target lang",
                user_message="Hedef dil belirtilmedi.",
                user_notify=True,
                log_level="info",
            )
        if source not in SUPPORTED_LANGS or target not in SUPPORTED_LANGS:
            return Error(
                message=f"unsupported lang ({source}->{target})",
                user_message="Bu dil çiftini henüz desteklemiyorum.",
                user_notify=True,
                log_level="info",
            )
        if target == "auto":
            return Error(
                message="auto cannot be target",
                user_message="Hedef dil 'auto' olamaz.",
                user_notify=True,
                log_level="info",
            )

        prompt = build_translation_user_message(
            text=text, source_lang=source, target_lang=target
        )

        try:
            translated = await self._gemini.generate_text(
                prompt, system=TRANSLATION_SYSTEM_PROMPT
            )
        except GeminiUnavailable as exc:
            logger.error("Translation Gemini call failed: %s", exc)
            return Error(
                message=str(exc),
                user_message="Çeviri servisi şu an yanıt vermiyor, biraz sonra dene.",
                retry_after=15,
            )

        return Success(
            data={
                "source_text": text,
                "translated_text": translated.strip(),
                "source_lang": source,
                "target_lang": target,
            },
            ui_type="TranslationCard",
        )

    def render_hint(self) -> str:
        return "TranslationCard"
