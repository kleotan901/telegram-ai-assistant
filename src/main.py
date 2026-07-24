import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.routers import analytics_router, webhook_router

from src.core.ai_client import ai_client, AIClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Lifespan ───────────────────────────────────────────────────
# asynccontextmanager перетворює звичайну async функцію
# в context manager для FastAPI lifespan.
#
# Код ДО yield → виконується при старті (startup)
# Код ПІСЛЯ yield → виконується при зупинці (shutdown)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle FastAPI додатку.

    Startup:
    1. Реєструємо webhook у Telegram (якщо WEBHOOK_URL заданий)
    2. Або запускаємо polling (для розробки)

    Shutdown:
    1. Видаляємо webhook
    2. Закриваємо з'єднання з ботом
    """
    # ── STARTUP ────────────────────────────────────────────────
    from src.bot.main_bot import bot, dp

    logger.info("Starting Telegram AI Assistant...")
    logger.info("Debug mode: %s", settings.debug)

    if settings.webhook_url:
        # ── Webhook mode (продакшн) ────────────────────────────
        webhook_url = f"{settings.webhook_url}/webhook/telegram"

        # Секретний токен Telegram
        secret_token = settings.bot_token.split(":")[0]

        await bot.set_webhook(
            url=webhook_url,
            secret_token=secret_token,
            drop_pending_updates=True,  # ігноруємо накопичені updates
            allowed_updates=[           # тільки ці типи updates
                "message",
                "callback_query",
                "inline_query",
            ],
        )

        webhook_info = await bot.get_webhook_info()
        logger.info(
            "Webhook set: url=%s, pending_updates=%d",
            webhook_info.url,
            webhook_info.pending_update_count,
        )

    else:
        # ── Polling mode (розробка) ────────────────────────────
        logger.info("WEBHOOK_URL not set, starting polling...")
        asyncio.create_task(
            dp.start_polling(
                bot,
                allowed_updates=dp.resolve_used_update_types(),
            )
        )

    logger.info("Bot started successfully")

    # ── Передаємо управління FastAPI ──────────────────────────
    yield

    # ── SHUTDOWN ───────────────────────────────────────────────
    logger.info("Shutting down...")

    if settings.webhook_url:
        await bot.delete_webhook(drop_pending_updates=False)
        logger.info("Webhook removed")

    await bot.session.close()
    logger.info("Bot session closed")

    # Закриваємо AI клієнт (звільняємо HTTP з'єднання)
    if isinstance(ai_client, AIClient):
        await ai_client.close()
        logger.info("AI client closed")


# ── FastAPI app ────────────────────────────────────────────────
app = FastAPI(
    title="Telegram AI Assistant",
    description=(
        "Multi-tenant AI bot with human handoff.\n\n"
        "## Features\n"
        "- 🤖 AI-powered responses\n"
        "- 🤝 Human handoff when confidence is low\n"
        "- 📊 Sales pipeline analytics\n"
        "- 📢 Broadcast messaging\n"
        "- ⏰ Follow-up reminders\n"
    ),
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan,
    # Документація доступна тільки в debug режимі
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)


# ── CORS ───────────────────────────────────────────────────────
#
# Дозволяємо крос-доменні запити для майбутнього дашборду.
# TODO У продакшні — обмежити конкретними доменами.
#
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ────────────────────────────────────────────────────
app.include_router(webhook_router)
app.include_router(analytics_router)


# ── Endpoints ──────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """Перевірка стану сервісу."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "debug": settings.debug,
        "webhook_mode": bool(settings.webhook_url),
    }


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"message": "Telegram AI Assistant API", "docs": "/docs"}
