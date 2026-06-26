from fastapi import FastAPI

from src.core.config import settings

app = FastAPI(
    title="Telegram AI Assistant",
    description="Multi-tenant AI bot with human handoff",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "0.1.0",
        "debug": settings.debug,
        "database_host": settings.postgres_host
    }
