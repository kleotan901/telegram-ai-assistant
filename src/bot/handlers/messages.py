import logging
import uuid

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.inline import get_response_keyboard
from src.core.config import settings
from src.db.fake_ai import FakeAIClient
from src.models.conversation import ConversationMode
from src.services import ConversationService, HandoffService

logger = logging.getLogger(__name__)

messages_router = Router(name="messages")

# ── Tenant ID ─────────────────────────────────────────────────
#
# У повноцінній multi-tenant системі tenant визначається
# за токеном бота або іншим ідентифікатором.
# TODO Поки що використовуємо один дефолтний tenant.
# TODO На Етапі 9 (Webhook) додамо повноцінну логіку.
#
DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@messages_router.message(F.text & ~F.text.startswith("/"))
async def handle_user_message(
    message: Message,
    session: AsyncSession,
) -> None:
    """
    Головний обробник текстових повідомлень.

    Фільтр: F.text — тільки текстові повідомлення
            ~F.text.startswith("/") — виключаємо команди

    Flow:
    1. Створюємо ConversationService
    2. Викликаємо handle_message
    3. Якщо mode=HUMAN — не відповідаємо (тренер відповість)
    4. Якщо потрібен handoff — повідомляємо тренерів
    5. Якщо mode=AI — відправляємо відповідь + inline кнопки
    """
    user = message.from_user
    if not user:
        return

    # Показуємо "пише..." поки обробляємо
    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action="typing",
    )

    # ── Ініціалізуємо сервіс ──────────────────────────────────
    conv_service = ConversationService(
        session=session,
        ai_client=FakeAIClient(),         # TODO ← замінимо на AIClient на Етапі 10
        tenant_id=DEFAULT_TENANT_ID,
    )

    # ── Обробляємо повідомлення ───────────────────────────────
    result = await conv_service.handle_message(
        telegram_id=user.id,
        text=message.text,
        username=user.username,
        full_name=user.full_name,
    )

    # ── HUMAN mode: тренер відповість сам ────────────────────
    if result.mode == ConversationMode.HUMAN and not result.need_human:
        # Вже були в HUMAN mode до цього повідомлення
        # Тренер побачить нове повідомлення у своєму чаті
        logger.info(
            "Message saved in HUMAN mode for user %s",
            user.id,
        )
        return

    # ── Handoff щойно спрацював ───────────────────────────────
    if result.need_human:
        handoff_service = HandoffService(
            session=session,
            tenant_id=DEFAULT_TENANT_ID,
        )

        # Отримуємо telegram_id тренерів
        trainer_ids = await handoff_service.activate_handoff(
            conversation_id=result.conversation_id,
        )

        # Повідомляємо кожного тренера
        for trainer_id in trainer_ids:
            try:
                await message.bot.send_message(
                    chat_id=trainer_id,
                    text=(
                        f"🔔 <b>Новий запит від користувача!</b>\n\n"
                        f"👤 User ID: <code>{user.id}</code>\n"
                        f"📝 Повідомлення: {message.text}\n\n"
                        f"Відповісти: /reply {user.id} [текст]"
                    ),
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(
                    "Failed to notify trainer %s: %s",
                    trainer_id, e,
                )

        # Повідомляємо користувача про handoff
        await message.answer(
            "🤝 Ваше запитання передано менеджеру.\n"
            "Він відповість найближчим часом!"
        )
        return

    # ── AI відповідь + inline кнопки ─────────────────────────
    if result.response_text:
        await message.answer(
            text=result.response_text,
            reply_markup=get_response_keyboard(),
        )
