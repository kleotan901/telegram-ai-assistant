import logging
import uuid

from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import UserStage
from src.repositories import UserRepository, ConversationRepository

logger = logging.getLogger(__name__)

callbacks_router = Router(name="callbacks")

DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@callbacks_router.callback_query(F.data.startswith("response:"))
async def handle_response_callback(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """
    Обробник inline кнопок YES / NO / LATER.

    F.data.startswith("response:") — фільтр по callback_data.
    Обробляє тільки наші кнопки, не чужі.

    callback.answer() — обов'язково викликати,
    інакше Telegram покаже "годинник" на кнопці вічно.
    """
    if not callback.from_user or not callback.data:
        await callback.answer()
        return

    action = callback.data.split(":")[1]  # "yes", "no", "later"

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(
        telegram_id=callback.from_user.id,
        tenant_id=DEFAULT_TENANT_ID,
    )

    if not user:
        await callback.answer("❌ Користувача не знайдено")
        return

    # ── Обробляємо дію ────────────────────────────────────────
    if action == "yes":
        # Підвищуємо стадію: NEW → CONTACTED або CONTACTED → INTERESTED
        stage_progression = {
            UserStage.NEW: UserStage.CONTACTED,
            UserStage.CONTACTED: UserStage.INTERESTED,
            UserStage.INTERESTED: UserStage.DEMO,
            UserStage.DEMO: UserStage.CLIENT,
            UserStage.CLIENT: UserStage.CLIENT,
        }
        next_stage = stage_progression.get(user.stage, user.stage)
        await user_repo.update_stage(user.id, next_stage)

        await callback.answer("✅ Дякуємо за підтвердження!")
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "Чудово! Наш менеджер зв'яжеться з вами для уточнення деталей. 🎉"
        )

    elif action == "no":
        await user_repo.update_stage(user.id, UserStage.NEW)
        await callback.answer("Зрозуміло!")
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "Добре, якщо передумаєте — напишіть нам! 😊"
        )

    elif action == "later":
        await callback.answer("⏰ Нагадаємо пізніше!")
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "Добре! Нагадаємо вам пізніше. "
            "Якщо з'являться питання — пишіть! 💬"
        )

    logger.info(
        "User %s pressed button: %s, stage: %s",
        callback.from_user.id,
        action,
        user.stage.value,
    )
