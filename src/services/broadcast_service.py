import uuid
import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories import UserRepository

logger = logging.getLogger(__name__)


@dataclass
class BroadcastResult:
    """Результат масової розсилки."""
    total: int           # скільки всього користувачів
    sent: int            # скільки успішно відправлено
    failed: int          # скільки не вдалось
    failed_ids: list[int] # telegram_id що не отримали


class BroadcastService:
    """
    Сервіс масових повідомлень.
    Відправляє повідомлення всім активним користувачам tenant.
    Повертає список telegram_id для відправки — сама не відправляє
    (не знає про aiogram).
    """

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.user_repo = UserRepository(session)

    async def get_recipients(self) -> list[int]:
        """
        Отримати telegram_id всіх активних користувачів.
        Handler ітерує цей список і відправляє повідомлення.
        """
        users = await self.user_repo.get_all_active(self.tenant_id)
        return [user.telegram_id for user in users]