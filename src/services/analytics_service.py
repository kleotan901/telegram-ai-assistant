import uuid
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User, UserStage
from src.repositories import UserRepository

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Сервіс аналітики sales pipeline.
    Рахує користувачів по стадіях, активних/неактивних.
    """

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.user_repo = UserRepository(session)

    async def get_pipeline_stats(self) -> dict:
        """
        Статистика по стадіях pipeline.
        Повертає:
        {
            "stages": {
                "new": 42,
                "contacted": 18,
                "interested": 7,
                "demo": 3,
                "client": 2
            },
            "total": 72,
            "active": 65,
            "inactive": 7
        }
        """
        stages_count = {}

        for stage in UserStage:
            users = await self.user_repo.get_by_stage(
                tenant_id=self.tenant_id,
                stage=stage,
            )
            stages_count[stage.value] = len(users)

        total = sum(stages_count.values())

        # Неактивні = не писали більше 7 днів
        inactive_since = datetime.now(timezone.utc) - timedelta(days=7)
        inactive = await self.user_repo.get_inactive_users(
            tenant_id=self.tenant_id,
            since=inactive_since,
        )

        return {
            "stages": stages_count,
            "total": total,
            "active": total - len(inactive),
            "inactive": len(inactive),
        }

    async def get_active_users_count(self) -> int:
        """Кількість активних користувачів tenant."""
        users = await self.user_repo.get_all_active(self.tenant_id)
        return len(users)
