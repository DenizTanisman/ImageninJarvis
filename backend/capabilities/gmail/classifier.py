"""Gemini-driven email classifier.

Takes a batch of :class:`MailSummary` from the GmailAdapter and returns
:class:`ClassifiedMail` for each, bucketing into important / dm / promo /
other. Calls below the confidence threshold collapse to ``other`` so
the dispatcher never shows a low-confidence guess as a hard category.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Literal

from services.gemini_client import GeminiClient, GeminiUnavailable

from .models import MailSummary
from .prompts import EMAIL_CLASSIFIER_SYSTEM_PROMPT, build_classify_user_message

logger = logging.getLogger(__name__)

CategoryKey = Literal["important", "dm", "promo", "other"]
VALID_CATEGORIES: tuple[CategoryKey, ...] = ("important", "dm", "promo", "other")
DEFAULT_CONFIDENCE_THRESHOLD = 0.85


@dataclass(frozen=True)
class ClassifiedMail:
    mail: MailSummary
    category: CategoryKey
    confidence: float
    summary: str
    needs_reply: bool


class EmailClassifierError(RuntimeError):
    pass


class EmailClassifier:
    def __init__(
        self,
        gemini: GeminiClient,
        *,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> None:
        self._gemini = gemini
        self._threshold = confidence_threshold

    async def classify_batch(self, mails: list[MailSummary]) -> list[ClassifiedMail]:
        if not mails:
            return []

        payload = [
            {
                "id": m.id,
                "from": m.from_addr,
                "subject": m.subject,
                "snippet": m.snippet,
                "date": m.date,
            }
            for m in mails
        ]
        user_msg = build_classify_user_message(json.dumps(payload, ensure_ascii=False))

        try:
            raw = await self._gemini.generate_json(
                user_msg, system=EMAIL_CLASSIFIER_SYSTEM_PROMPT
            )
        except GeminiUnavailable as exc:
            raise EmailClassifierError(f"Gemini unreachable: {exc}") from exc
        except ValueError as exc:
            raise EmailClassifierError(f"Gemini returned non-JSON: {exc}") from exc

        if not isinstance(raw, list):
            raise EmailClassifierError(
                f"Gemini returned non-array response: {type(raw).__name__}"
            )

        by_id = {m.id: m for m in mails}
        results: list[ClassifiedMail] = []
        seen_ids: set[str] = set()
        for entry in raw:
            classified = self._coerce_entry(entry, by_id)
            if classified is None:
                continue
            seen_ids.add(classified.mail.id)
            results.append(classified)

        # Mails the model dropped on the floor fall back to "other" with
        # zero confidence so callers can still render them.
        for mail in mails:
            if mail.id not in seen_ids:
                results.append(_fallback_other(mail))

        return results

    def _coerce_entry(
        self, entry: object, by_id: dict[str, MailSummary]
    ) -> ClassifiedMail | None:
        if not isinstance(entry, dict):
            return None
        mail_id = entry.get("id")
        if not isinstance(mail_id, str):
            return None
        mail = by_id.get(mail_id)
        if mail is None:
            return None

        try:
            confidence = float(entry.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        category_raw = entry.get("category")
        if category_raw not in VALID_CATEGORIES or confidence < self._threshold:
            category: CategoryKey = "other"
        else:
            category = category_raw  # type: ignore[assignment]

        summary = entry.get("summary")
        if not isinstance(summary, str):
            summary = mail.subject

        needs_reply = bool(entry.get("needs_reply", False))

        return ClassifiedMail(
            mail=mail,
            category=category,
            confidence=confidence,
            summary=summary[:200],
            needs_reply=needs_reply,
        )


def _fallback_other(mail: MailSummary) -> ClassifiedMail:
    return ClassifiedMail(
        mail=mail,
        category="other",
        confidence=0.0,
        summary=mail.subject or mail.snippet[:140],
        needs_reply=False,
    )
