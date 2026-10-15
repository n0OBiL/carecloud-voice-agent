from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI

from app.api.patients import router as patients_router
from app.database import init_db
from app.voice.webhooks import router as voice_router

app = FastAPI(title="CareCloud Voice Agent", version="1.0.0")


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/")
def read_root() -> dict:
    return {
        "message": "CareCloud Voice Agent API",
        "docs": "/docs",
        "version": app.version,
    }


@app.get("/health")
def health_check() -> dict:
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": "development",
    }


app.include_router(patients_router, prefix="/api")
app.include_router(voice_router)
