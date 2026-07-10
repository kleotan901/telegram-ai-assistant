import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.conversation import ConversationMode
from src.models.message import MessageRole
from src.repositories import (
    ConversationRepository,
    MessageRepository,
    TrainerRepository,
    UserRepository,
)

logger = logging.getLogger(__name__)


class HandoffService:
    """
    Сервіс управління переключенням між AI і тренером.

    Відповідає за:
    - Активацію HUMAN режиму
    - Повернення в AI режим (/resume)
    - Обробку команди /reply від тренера
    - Збереження системних повідомлень про handoff

    НЕ відповідає за:
    - Відправку Telegram повідомлень (це handler)
    - Вирішення коли потрібен handoff (це ConversationService)
    """

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id

        self.conv_repo = ConversationRepository(session)
        self.msg_repo = MessageRepository(session)
        self.trainer_repo = TrainerRepository(session)
        self.user_repo = UserRepository(session)

    async def activate_handoff(
        self,
        conversation_id: uuid.UUID,
    ) -> list[int]:
        """
        Активувати human handoff для розмови.

        1. Перемикає conversation.mode = HUMAN
        2. Зберігає системне повідомлення
        3. Повертає список telegram_id активних тренерів
           (щоб handler міг їх повідомити)

        Повертає список telegram_id — не відправляє сам,
        бо не знає про aiogram.
        """
        # Перемикаємо режим
        await self.conv_repo.set_mode(
            conversation_id,
            ConversationMode.HUMAN,
        )

        # Системне повідомлення в історію
        await self.msg_repo.create_message(
            conversation_id=conversation_id,
            tenant_id=self.tenant_id,
            role=MessageRole.SYSTEM,
            content="[HANDOFF] Розмову передано тренеру",
        )

        # Отримуємо тренерів для повідомлення
        trainers = await self.trainer_repo.get_active_trainers(
            self.tenant_id
        )

        trainer_ids = [t.telegram_id for t in trainers]
        logger.info(
            "Handoff activated for conversation %s, "
            "notifying trainers: %s",
            conversation_id,
            trainer_ids,
        )
        return trainer_ids

    async def process_trainer_reply(
        self,
        trainer_telegram_id: int,
        target_user_telegram_id: int,
        reply_text: str,
    ) -> int | None:
        """
        Обробити команду /reply <user_id> від тренера.

        1. Перевіряє що тренер існує і активний
        2. Знаходить користувача і його активну розмову
        3. Зберігає повідомлення тренера в БД
        4. Повертає telegram_id користувача
           (щоб handler відправив йому відповідь)

        Повертає None якщо щось пішло не так.
        """
        # Перевіряємо тренера
        trainer = await self.trainer_repo.get_by_telegram_id(
            telegram_id=trainer_telegram_id,
            tenant_id=self.tenant_id,
        )
        if not trainer:
            logger.warning(
                "Unknown trainer tried to reply: %s",
                trainer_telegram_id,
            )
            return None

        # Знаходимо цільового користувача
        user = await self.user_repo.get_by_telegram_id(
            telegram_id=target_user_telegram_id,
            tenant_id=self.tenant_id,
        )
        if not user:
            logger.warning(
                "Target user not found: %s",
                target_user_telegram_id,
            )
            return None

        # Знаходимо активну розмову
        conversation = await self.conv_repo.get_active(
            user_id=user.id,
            tenant_id=self.tenant_id,
        )
        if not conversation:
            logger.warning(
                "No active conversation for user %s",
                user.id,
            )
            return None

        # Зберігаємо повідомлення тренера
        await self.msg_repo.create_message(
            conversation_id=conversation.id,
            tenant_id=self.tenant_id,
            role=MessageRole.TRAINER,
            content=reply_text,
        )

        logger.info(
            "Trainer %s replied to user %s",
            trainer_telegram_id,
            target_user_telegram_id,
        )
        return user.telegram_id

    async def resume_ai(
        self,
        target_user_telegram_id: int,
    ) -> bool:
        """
        Повернути розмову в AI режим (/resume команда).

        1. Знаходить розмову
        2. Перемикає mode = AI
        3. Зберігає системне повідомлення
        4. Повертає True якщо успішно
        """
        user = await self.user_repo.get_by_telegram_id(
            telegram_id=target_user_telegram_id,
            tenant_id=self.tenant_id,
        )
        if not user:
            return False

        conversation = await self.conv_repo.get_active(
            user_id=user.id,
            tenant_id=self.tenant_id,
        )
        if not conversation:
            return False

        await self.conv_repo.set_mode(
            conversation.id,
            ConversationMode.AI,
        )

        await self.msg_repo.create_message(
            conversation_id=conversation.id,
            tenant_id=self.tenant_id,
            role=MessageRole.SYSTEM,
            content="[RESUME] Розмову повернуто в режим AI",
        )

        logger.info(
            "AI resumed for user %s (conversation %s)",
            target_user_telegram_id,
            conversation.id,
        )
        return True

    async def get_pending_handoffs(self) -> list[dict]:
        """
        Список розмов що очікують відповіді тренера.
        Використовується для команди /pending або дашборду тренера.
        """
        conversations = await self.conv_repo.get_human_mode_conversations(
            self.tenant_id
        )

        result = []
        for conv in conversations:
            user = await self.user_repo.get(conv.user_id)
            if user:
                result.append({
                    "conversation_id": str(conv.id),
                    "user_telegram_id": user.telegram_id,
                    "username": user.username,
                    "full_name": user.full_name,
                })
        return result
