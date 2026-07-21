import logging
import uuid

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.services import HandoffService

logger = logging.getLogger(__name__)

trainer_router = Router(name="trainer")

DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@trainer_router.message(Command("reply"))
async def cmd_reply(message: Message, session: AsyncSession) -> None:
    """
    Команда тренера: /reply <user_telegram_id> <текст відповіді>

    Приклад: /reply 123456789 Привіт! Ціна залежить від обсягу.

    Парсимо аргументи вручну — aiogram не має вбудованого
    парсера аргументів команд.
    """
    if not message.text or not message.from_user:
        return

    # Парсимо: "/reply 123456 Текст відповіді"
    parts = message.text.split(maxsplit=2)

    if len(parts) < 3:
        await message.answer(
            "❌ Невірний формат.\n"
            "Використання: /reply <user_id> <текст>\n"
            "Приклад: /reply 123456789 Ціна від $29"
        )
        return

    # parts[0] = "/reply", parts[1] = user_id, parts[2] = текст
    try:
        target_user_id = int(parts[1])
    except ValueError:
        await message.answer(
            "❌ user_id повинен бути числом.\n"
            f"Отримано: {parts[1]!r}"
        )
        return

    reply_text = parts[2]

    handoff_service = HandoffService(
        session=session,
        tenant_id=DEFAULT_TENANT_ID,
    )

    # Обробляємо відповідь тренера
    user_telegram_id = await handoff_service.process_trainer_reply(
        trainer_telegram_id=message.from_user.id,
        target_user_telegram_id=target_user_id,
        reply_text=reply_text,
    )

    if user_telegram_id is None:
        await message.answer(
            f"❌ Не вдалось відправити відповідь.\n"
            f"Перевірте чи правильний user_id: {target_user_id}"
        )
        return

    # Відправляємо відповідь користувачу
    try:
        await message.bot.send_message(
            chat_id=user_telegram_id,
            text=f"👤 <b>Менеджер:</b> {reply_text}",
            parse_mode="HTML",
        )
        await message.answer(
            f"✅ Відповідь надіслано користувачу {user_telegram_id}"
        )
    except Exception as e:
        logger.error(
            "Failed to send reply to user %s: %s",
            user_telegram_id, e,
        )
        await message.answer(
            f"❌ Помилка при відправці: {e}"
        )


@trainer_router.message(Command("resume"))
async def cmd_resume(message: Message, session: AsyncSession) -> None:
    """
    Команда тренера: /resume <user_telegram_id>

    Повертає розмову в AI режим.
    Приклад: /resume 123456789
    """
    if not message.text or not message.from_user:
        return

    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "❌ Невірний формат.\n"
            "Використання: /resume <user_id>\n"
            "Приклад: /resume 123456789"
        )
        return

    try:
        target_user_id = int(parts[1])
    except ValueError:
        await message.answer(
            f"❌ user_id повинен бути числом. Отримано: {parts[1]!r}"
        )
        return

    handoff_service = HandoffService(
        session=session,
        tenant_id=DEFAULT_TENANT_ID,
    )

    success = await handoff_service.resume_ai(
        target_user_telegram_id=target_user_id,
    )

    if success:
        await message.answer(
            f"✅ Розмову з користувачем {target_user_id} "
            f"повернуто в режим AI."
        )
        # Повідомляємо користувача
        try:
            await message.bot.send_message(
                chat_id=target_user_id,
                text="🤖 Продовжуємо спілкування в автоматичному режимі!",
            )
        except Exception as e:
            logger.warning(
                "Could not notify user %s about resume: %s",
                target_user_id, e,
            )
    else:
        await message.answer(
            f"❌ Не вдалось знайти активну розмову "
            f"для користувача {target_user_id}."
        )


@trainer_router.message(Command("pending"))
async def cmd_pending(message: Message, session: AsyncSession) -> None:
    """
    Команда тренера: /pending
    Показує список розмов що очікують відповіді тренера.
    """
    handoff_service = HandoffService(
        session=session,
        tenant_id=DEFAULT_TENANT_ID,
    )

    pending = await handoff_service.get_pending_handoffs()

    if not pending:
        await message.answer("✅ Немає активних запитів. Все оброблено!")
        return

    lines = [f"📋 <b>Очікують відповіді ({len(pending)}):</b>\n"]
    for item in pending:
        name = item["full_name"] or item["username"] or "Невідомий"
        lines.append(
            f"• {name} "
            f"(ID: <code>{item['user_telegram_id']}</code>)\n"
            f"  /reply {item['user_telegram_id']} [текст]"
        )

    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
    )
