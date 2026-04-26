"""FastAPI entry point."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes.auth import router as auth_router
from app.routes.calendar import router as calendar_router
from app.routes.chat import router as chat_router
from app.routes.mail import router as mail_router
from app.routes.translation import router as translation_router
from app.routes.upload import router as upload_router

settings = get_settings()

app = FastAPI(
    title="Jarvis API",
    version="0.1.0",
    description="Mode-agnostic personal assistant backend.",
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
