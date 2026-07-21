import asyncio
import logging

from fastapi import FastAPI

from src.core.config import settings
from src.bot.main_bot import bot, dp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Telegram AI Assistant",
    description="Multi-tenant AI bot with human handoff",
    version="0.1.0",
    debug=settings.debug,
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


async def start_polling():
    """
    Polling режим — для локальної розробки без публічного URL.

    Бот сам питає Telegram "чи є нові повідомлення?"
    кожні кілька секунд. Не потрібен HTTPS і публічний домен.

    TODO Для продакшну — використовуємо Webhook (Етап 9).
    """

    logger.info("Starting bot in polling mode...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(start_polling())
