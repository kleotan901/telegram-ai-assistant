import uuid

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.trainer import Trainer
from src.repositories.base_repository import BaseRepository


class TrainerRepository(BaseRepository[Trainer]):
    """
    Репозиторій для роботи з тренерами.
    """

    model = Trainer

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_telegram_id(
        self,
        telegram_id: int,
        tenant_id: uuid.UUID,
    ) -> Trainer | None:
        """Знайти тренера за telegram_id."""
        result = await self.session.execute(
            select(Trainer).where(
                and_(
                    Trainer.telegram_id == telegram_id,
                    Trainer.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_active_trainers(
        self,
        tenant_id: uuid.UUID,
    ) -> list[Trainer]:
        """
        Всі активні тренери tenant.

        При human handoff — повідомляємо всіх активних тренерів.
        """
        result = await self.session.execute(
            select(Trainer).where(
                and_(
                    Trainer.tenant_id == tenant_id,
                    Trainer.is_active == True,  # noqa: E712
                )
            )
        )
        return list(result.scalars().all())