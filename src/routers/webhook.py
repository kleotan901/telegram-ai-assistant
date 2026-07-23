import logging

from aiogram.types import Update
from fastapi import APIRouter, Header, HTTPException, Request, status

from src.bot.main_bot import bot, dp
from src.core.config import settings

logger = logging.getLogger(__name__)

webhook_router = APIRouter(prefix="/webhook", tags=["webhook"])

# Secret token для верифікації що запит від Telegram
# Генерується один раз і передається при setWebhook
WEBHOOK_SECRET = settings.bot_token.split(":")[0]  # використовуємо частину токена


@webhook_router.post(
    "/telegram",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,  # не показуємо в Swagger
)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(
        default=None,
        alias="X-Telegram-Bot-Api-Secret-Token",
    ),
) -> dict:
    """
    Endpoint що приймає updates від Telegram.

    Telegram надсилає POST запит на цей URL кожного разу
    коли хтось пише боту.

    Безпека:
    - X-Telegram-Bot-Api-Secret-Token — секретний токен
      що ми передали при setWebhook. Якщо хтось інший
      спробує POST на цей endpoint — запит відхилиться.

    Чому повертаємо {"ok": True}?
    Telegram очікує HTTP 200. Якщо отримає інше — буде
    retry кілька разів з наростаючою затримкою.
    """
    # ── Верифікація WEBHOOK_SECRET ─────────────────────────
    if x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        logger.warning(
            "Invalid webhook secret token: %r",
            x_telegram_bot_api_secret_token,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid secret token",
        )

    # ── Парсимо тіло запиту як Telegram Update ─────────────────
    try:
        body = await request.json()
    except Exception as e:
        logger.error("Failed to parse webhook body: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        )

    # ── Передаємо update в aiogram Dispatcher ─────────────────
    #
    # Update.model_validate(body) — парсить JSON в aiogram Update
    # dp.feed_update() — передає update на обробку handlers
    #
    try:
        telegram_update = Update.model_validate(body)
        await dp.feed_update(bot=bot, update=telegram_update)
    except Exception as e:
        logger.error("Failed to process update: %s", e)
        # Повертаємо 200 навіть при помилці —
        # інакше Telegram буде ретраїти нескінченно
        return {"ok": False, "error": str(e)}

    return {"ok": True}
