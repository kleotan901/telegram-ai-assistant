import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings

logger = logging.getLogger(__name__)

# Роутер для команд — реєструється в main_bot.py
commands_router = Router(name="commands")


@commands_router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    """
    Обробник команди /start.

    CommandStart() — спеціальний фільтр aiogram для /start.
    Він також обробляє /start з параметром: /start ref_123

    session передається автоматично через DbSessionMiddleware —
    aiogram бачить параметр 'session: AsyncSession' і підставляє
    його з data["session"].
    """
    user = message.from_user
    if not user:
        return

    logger.info("User %s started bot", user.id)

    await message.answer(
        f"Привіт, {user.full_name}! 👋\n\n"
        "Я AI-асистент. Напишіть ваше запитання і я одразу відповім.\n\n"
        "Якщо знадобиться допомога живої людини — "
        "я автоматично підключу менеджера. 🤝"
    )


@commands_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Обробник команди /help."""
    await message.answer(
        "🤖 <b>Як я працюю:</b>\n\n"
        "• Надсилайте будь-які запитання\n"
        "• Я відповідаю автоматично\n"
        "• При складних питаннях — підключаю менеджера\n\n"
        "📞 <b>Кнопки відповіді:</b>\n"
        "• <b>Так</b> — підтвердити інтерес\n"
        "• <b>Ні</b> — відмовитись\n"
        "• <b>Пізніше</b> — нагадати пізніше",
        parse_mode="HTML",
    )
    