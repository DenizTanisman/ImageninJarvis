"""Async Gemini client with retry + concurrency cap.

The classifier and capability strategies depend on this client. We wrap
``google-generativeai`` so we can:
- bound concurrency with an ``asyncio.Semaphore`` (avoid hammering quota),
- retry transient failures with exponential backoff via tenacity,
- swap the underlying model in tests by passing ``model=`` directly.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import google.generativeai as genai
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.0-flash"
DEFAULT_MAX_CONCURRENT = 5
DEFAULT_MAX_ATTEMPTS = 3


class GeminiUnavailable(Exception):
    """Raised when Gemini is unreachable after exhausting retries."""


class GeminiClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_name: str = DEFAULT_MODEL,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        model: Any | None = None,
    ) -> None:
        if model is not None:
            self._model = model
        else:
            if not api_key:
                raise ValueError("Either api_key or model must be provided")
            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel(model_name)

        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_attempts = max_attempts

    async def generate_text(
        self,
        prompt: str,
        *,
        system: str | None = None,
    ) -> str:
        """Return plain-text completion. Raises GeminiUnavailable on retry exhaustion."""
        contents = self._build_contents(prompt, system)
        response = await self._call_with_retry(contents)
        return _extract_text(response)

    async def generate_json(
        self,
        prompt: str,
        *,
        system: str | None = None,
    ) -> Any:
        """Parse the model's response as JSON. Raises ValueError if not parseable."""
        text = await self.generate_text(prompt, system=system)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            cleaned = _strip_code_fence(text)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                raise ValueError(f"Gemini response was not valid JSON: {text[:200]!r}") from exc

    async def _call_with_retry(self, contents: Any) -> Any:
        async with self._semaphore:
            try:
                async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(self._max_attempts),
                    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
                    retry=retry_if_exception_type(Exception),
                    reraise=False,
                ):
                    with attempt:
                        return await self._model.generate_content_async(contents)
            except RetryError as exc:
                logger.error("Gemini retries exhausted: %s", exc.last_attempt.exception())
                raise GeminiUnavailable("Gemini is unreachable") from exc
        raise GeminiUnavailable("Gemini retry loop exited without result")

    @staticmethod
    def _build_contents(prompt: str, system: str | None) -> list[str] | str:
        if system:
            return [system, prompt]
        return prompt


def _extract_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text
    raise ValueError("Gemini response is missing .text")


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1]
        if stripped.endswith("```"):
            stripped = stripped[: stripped.rfind("```")]
    return stripped.strip()
