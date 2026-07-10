import uuid
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories import UserRepository

logger = logging.getLogger(__name__)

# Константи follow-up логіки
FOLLOWUP_AFTER_HOURS = 24
FOLLOWUP_MESSAGE = (
    "Привіт! 👋 Просто хотіли перевірити — "
    "чи вам ще потрібна допомога?"
)


class FollowUpService:
    """
    Сервіс follow-up повідомлень.
    APScheduler викликає check_and_send() кожну годину.
    Сервіс знаходить користувачів що не писали > 24 годин
    і повертає їх telegram_id для відправки follow-up.
    """

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.user_repo = UserRepository(session)

    async def get_users_for_followup(self) -> list[int]:
        """
        Знайти користувачів що потребують follow-up.

        Критерії:
        - Активний (is_active=True)
        - Не писав більше FOLLOWUP_AFTER_HOURS годин
        """
        since = datetime.now(timezone.utc) - timedelta(
            hours=FOLLOWUP_AFTER_HOURS
        )

        inactive_users = await self.user_repo.get_inactive_users(
            tenant_id=self.tenant_id,
            since=since,
        )

        telegram_ids = [u.telegram_id for u in inactive_users]

        if telegram_ids:
            logger.info(
                "Follow-up needed for %d users in tenant %s",
                len(telegram_ids),
                self.tenant_id,
            )

        return telegram_ids

    @staticmethod
    def get_followup_message() -> str:
        """Текст follow-up повідомлення."""
        return FOLLOWUP_MESSAGE
