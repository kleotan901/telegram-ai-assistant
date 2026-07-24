import logging
import uuid

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.inline import get_response_keyboard
from src.core.ai_client import ai_client
from src.models.conversation import ConversationMode
from src.services import ConversationService, HandoffService

logger = logging.getLogger(__name__)

messages_router = Router(name="messages")
DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@messages_router.message(F.text & ~F.text.startswith("/"))
async def handle_user_message(
    message: Message,
    session: AsyncSession,
) -> None:
    user = message.from_user
    if not user or not message.text:
        return

    logger.info(
        "Message from user=%s text=%r",
        user.id, message.text
    )

    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action="typing",
    )

    conv_service = ConversationService(
        session=session,
        ai_client=ai_client,
        tenant_id=DEFAULT_TENANT_ID,
    )

    result = await conv_service.handle_message(
        telegram_id=user.id,
        text=message.text,
        username=user.username,
        full_name=user.full_name,
    )

    logger.info(
        "Result: mode=%s need_human=%s",
        result.mode, result.need_human
    )

    # ── Вже були в HUMAN mode до цього повідомлення ───────────
    # need_human=True але mode вже був HUMAN → не активуємо знову
    if (
        result.mode == ConversationMode.HUMAN
        and not result.need_human
    ):
        # Повідомляємо тренерів що є нове повідомлення
        handoff_service = HandoffService(
            session=session,
            tenant_id=DEFAULT_TENANT_ID,
        )
        pending = await handoff_service.get_pending_handoffs()
        logger.info(
            "User %s wrote in HUMAN mode, pending handoffs: %d",
            user.id, len(pending)
        )
        # Нічого не відправляємо користувачу —
        # тренер відповість через /reply
        return

    # ── Handoff щойно спрацював ───────────────────────────────
    if result.need_human:
        handoff_service = HandoffService(
            session=session,
            tenant_id=DEFAULT_TENANT_ID,
        )

        trainer_ids = await handoff_service.activate_handoff(
            conversation_id=result.conversation_id,
        )

        for trainer_id in trainer_ids:
            try:
                await message.bot.send_message(
                    chat_id=trainer_id,
                    text=(
                        f"🔔 <b>Новий запит!</b>\n\n"
                        f"👤 ID: <code>{user.id}</code>\n"
                        f"📝 {message.text}\n\n"
                        f"/reply {user.id} [відповідь]"
                    ),
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error("Failed to notify trainer %s: %s", trainer_id, e)

        await message.answer(
            "🤝 Ваше запитання передано менеджеру.\n"
            "Він відповість найближчим часом!"
        )
        return

    # ── AI відповідь ──────────────────────────────────────────
    if result.response_text:
        await message.answer(
            text=result.response_text,
            reply_markup=get_response_keyboard(),
        )
