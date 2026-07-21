import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.bot.handlers.callbacks import callbacks_router
from src.bot.handlers.commands import commands_router
from src.bot.handlers.messages import messages_router
from src.bot.handlers.trainer_commands import trainer_router
from src.bot.middlewares.db_session import DbSessionMiddleware
from src.core.config import settings
from src.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


def create_bot() -> Bot:
    """
    Створити Bot екземпляр.

    DefaultBotProperties — глобальні налаштування для всіх
    повідомлень бота. parse_mode=HTML означає що всі
    message.answer() з HTML тегами будуть рендеритись правильно
    без необхідності вказувати parse_mode кожного разу.
    """

    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
        ),
    )


def create_dispatcher() -> Dispatcher:
    """
    Створити і налаштувати Dispatcher.

    Dispatcher — це центральний об'єкт aiogram що:
    1. Реєструє middleware
    2. Підключає роутери
    3. Маршрутизує updates до правильних handlers

    Порядок реєстрації роутерів важливий:
    trainer_router першим — щоб /reply і /resume не перехоплювались
    іншими роутерами.
    """
    dp = Dispatcher()

    # ── Middleware ─────────────────────────────────────────────
    # update.middleware — виконується для ВСІХ типів updates
    # (messages, callbacks, inline queries тощо)
    dp.update.middleware(
        DbSessionMiddleware(session_factory=AsyncSessionLocal)
    )

    # ── Роутери (порядок має значення) ────────────────────────
    dp.include_router(commands_router)      # /start, /help
    dp.include_router(trainer_router)       # /reply, /resume, /pending
    dp.include_router(callbacks_router)     # inline кнопки
    dp.include_router(messages_router)      # всі текстові повідомлення

    logger.info("Dispatcher created with %d routers", 4)
    return dp


# Глобальні екземпляри — створюються один раз при старті
bot = create_bot()
dp = create_dispatcher()
