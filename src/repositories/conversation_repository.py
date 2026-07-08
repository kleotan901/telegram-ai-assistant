import uuid

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.conversation import Conversation, ConversationMode
from src.repositories.base_repository import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """
    Репозиторій для роботи з розмовами.
    """

    model = Conversation
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_active(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Conversation | None:
        """
        Отримати активну розмову користувача.
        У кожного користувача тільки одна активна розмова.
        """
        result = await self.session.execute(
            select(Conversation).where(
                and_(
                    Conversation.user_id == user_id,
                    Conversation.tenant_id == tenant_id,
                    Conversation.is_active == True,  # noqa: E712
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_active(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> tuple[Conversation, bool]:
        """
        Отримати активну розмову або створити нову.
        Якщо активна розмова є — повертаємо її.
        Якщо немає — створюємо нову в режимі AI.
        """
        conversation = await self.get_active(user_id, tenant_id)

        if conversation is not None:
            return conversation, False

        conversation = await self.create(
            user_id=user_id,
            tenant_id=tenant_id,
            mode=ConversationMode.AI,
            is_active=True,
        )
        return conversation, True

    async def set_mode(
        self,
        conversation_id: uuid.UUID,
        mode: ConversationMode,
    ) -> Conversation | None:
        """
        Перемкнути режим розмови: AI ↔ HUMAN.
        Викликається HandoffService при низькому confidence
        або командою /resume від тренера.
        """
        return await self.update(conversation_id, mode=mode)

    async def close(
        self,
        conversation_id: uuid.UUID,
    ) -> Conversation | None:
        """Закрити розмову (is_active=False)."""
        return await self.update(
            conversation_id,
            is_active=False,
        )

    async def get_human_mode_conversations(
        self,
        tenant_id: uuid.UUID,
    ) -> list[Conversation]:
        """
        Всі розмови у режимі HUMAN для tenant.
        Тренер бачить список розмов які чекають на його відповідь.
        """
        result = await self.session.execute(
            select(Conversation).where(
                and_(
                    Conversation.tenant_id == tenant_id,
                    Conversation.mode == ConversationMode.HUMAN,
                    Conversation.is_active == True,  # noqa: E712
                )
            )
        )
        return list(result.scalars().all())
