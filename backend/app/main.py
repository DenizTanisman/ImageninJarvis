"""FastAPI entry point."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes.auth import router as auth_router
from app.routes.calendar import router as calendar_router
from app.routes.chat import router as chat_router
from app.routes.document import router as document_router
from app.routes.drive import router as drive_router
from app.routes.mail import router as mail_router
from app.routes.translation import router as translation_router
from app.routes.upload import router as upload_router
from capabilities.document.ingest import sweep_old_sandboxes

logger = logging.getLogger(__name__)
settings = get_settings()

# Run the sandbox sweep once an hour by default; >24h folders are
# removed on each tick so a crashed worker can't leak files indefinitely.
SANDBOX_SWEEP_INTERVAL_SECONDS = 60 * 60


@asynccontextmanager
async def lifespan(app: FastAPI):
    sweep_task = asyncio.create_task(_sandbox_sweep_loop())
    try:
        yield
    finally:
        sweep_task.cancel()
        try:
            await sweep_task
        except asyncio.CancelledError:
            pass


async def _sandbox_sweep_loop() -> None:
    sandbox_root = Path(settings.sandbox_dir)
    while True:
        try:
            removed = sweep_old_sandboxes(sandbox_root)
            if removed:
                logger.info("Sandbox sweep removed %d stale directories", removed)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Sandbox sweep loop iteration failed: %s", exc)
        await asyncio.sleep(SANDBOX_SWEEP_INTERVAL_SECONDS)


app = FastAPI(
    title="Jarvis API",
    version="0.1.0",
    description="Mode-agnostic personal assistant backend.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(mail_router)
app.include_router(translation_router)
app.include_router(calendar_router)
app.include_router(upload_router)
app.include_router(document_router)
app.include_router(drive_router)
