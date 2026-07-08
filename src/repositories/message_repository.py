import uuid

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.message import Message, MessageRole
from src.repositories.base_repository import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """
    Репозиторій для збереження і читання повідомлень.
    """

    model = Message

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create_message(
        self,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        role: MessageRole,
        content: str,
        confidence: float | None = None,
        need_human: bool = False,
    ) -> Message:
        """
        Зберегти повідомлення.

        Обгортка над create() з явними параметрами —
        щоб не передавати словник kwargs.
        """
        return await self.create(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            role=role,
            content=content,
            confidence=confidence,
            need_human=need_human,
        )

    async def get_history(
        self,
        conversation_id: uuid.UUID,
        limit: int = 20,
    ) -> list[Message]:
        """
        Отримати останні N повідомлень розмови.

        Сортуємо за created_at ASC щоб отримати
        хронологічний порядок (старі → нові).
        Limit обмежує контекст для AI API.
        """
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_last_user_message(
        self,
        conversation_id: uuid.UUID,
    ) -> Message | None:
        """
        Останнє повідомлення від користувача.
        Використовується для перевірки чи потрібен follow-up.
        """
        result = await self.session.execute(
            select(Message)
            .where(
                and_(
                    Message.conversation_id == conversation_id,
                    Message.role == MessageRole.USER,
                )
            )
            .order_by(desc(Message.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()
