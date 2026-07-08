import uuid
from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User, UserStage
from src.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    Репозиторій для роботи з таблицею users.
    Містить специфічні запити для User моделі поверх базових CRUD.
    """
    model = User

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_telegram_id(
        self,
        telegram_id: int,
        tenant_id: uuid.UUID,
    ) -> User | None:
        """
        Знайти користувача за telegram_id в межах tenant.

        Чому і tenant_id, і telegram_id?
        Один Telegram-користувач може взаємодіяти з ботами
        різних tenant. Пара (telegram_id, tenant_id) унікальна.
        """
        result = await self.session.execute(
            select(User).where(
                and_(
                    User.telegram_id == telegram_id,
                    User.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        telegram_id: int,
        tenant_id: uuid.UUID,
        username: str | None = None,
        full_name: str | None = None,
    ) -> tuple[User, bool]:
        """
        Отримати існуючого або створити нового користувача.
        Повертає tuple (user, created):
          created=True  — щойно створено
          created=False — вже існував

        Цей патерн використовується в обробнику кожного
        повідомлення — ми не знаємо чи пише нова людина
        чи вже зареєстрована.
        """
        user = await self.get_by_telegram_id(telegram_id, tenant_id)

        if user is not None:
            # Оновлюємо username/full_name якщо змінились в Telegram
            await self.update(
                user.id,
                username=username,
                full_name=full_name,
                last_seen_at=datetime.now(timezone.utc),
            )
            await self.session.refresh(user)
            return user, False

        user = await self.create(
            tenant_id=tenant_id,
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            stage=UserStage.NEW,
        )
        return user, True

    async def update_stage(
        self,
        user_id: uuid.UUID,
        stage: UserStage,
    ) -> User | None:
        """Змінити стадію користувача в sales pipeline."""
        return await self.update(user_id, stage=stage)

    async def update_last_seen(
        self,
        user_id: uuid.UUID,
    ) -> None:
        """Оновити час останньої активності."""
        await self.update(
            user_id,
            last_seen_at=datetime.now(timezone.utc),
        )

    async def get_by_stage(
        self,
        tenant_id: uuid.UUID,
        stage: UserStage,
    ) -> list[User]:
        """Отримати всіх користувачів на певній стадії."""
        result = await self.session.execute(
            select(User).where(
                and_(
                    User.tenant_id == tenant_id,
                    User.stage == stage,
                    User.is_active == True,  # noqa: E712
                )
            )
        )
        return list(result.scalars().all())

    async def get_inactive_users(
        self,
        tenant_id: uuid.UUID,
        since: datetime,
    ) -> list[User]:
        """
        Отримати користувачів що не писали з певного часу.

        Використовується APScheduler для follow-up:
        'знайди всіх хто не писав більше 24 годин'
        """
        result = await self.session.execute(
            select(User).where(
                and_(
                    User.tenant_id == tenant_id,
                    User.is_active == True,  # noqa: E712
                    User.last_seen_at < since,
                )
            )
        )
        return list(result.scalars().all())

    async def get_all_active(
        self,
        tenant_id: uuid.UUID,
    ) -> list[User]:
        """Всі активні користувачі tenant — для broadcast."""
        result = await self.session.execute(
            select(User).where(
                and_(
                    User.tenant_id == tenant_id,
                    User.is_active == True,  # noqa: E712
                )
            )
        )
        return list(result.scalars().all())