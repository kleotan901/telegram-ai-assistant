import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import Base

# T — це TypeVar який замінюється конкретною моделлю
# при оголошенні репозиторію: BaseRepository[User]
T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """
    Базовий репозиторій з універсальними CRUD операціями.

    Використання:
        class UserRepository(BaseRepository[User]):
            model = User

    Нащадок отримує безкоштовно:
        get, create, update, delete, list, count
    """

    model: type[T]  # конкретна модель, оголошується в нащадках

    def __init__(self, session: AsyncSession) -> None:
        """
        session передається ззовні (dependency injection).
        Репозиторій НЕ створює сесію сам — він її отримує.
        Це дозволяє кільком репозиторіям ділити одну транзакцію.
        """
        self.session = session

    async def get(self, id: uuid.UUID) -> T | None:
        """
        Отримати один запис за первинним ключем.
        Повертає None якщо не знайдено (не кидає виключення).
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """
        Отримати список записів з пагінацією.

        * (keyword-only) — limit і offset можна передавати
        тільки як іменовані аргументи, не позиційні.
        Це захист від помилки: get_all(50, 0) замість
        get_all(limit=50, offset=0).
        """
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        """Загальна кількість записів у таблиці."""
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()

    # ── CREATE ────────────────────────────────────────────────

    async def create(self, **kwargs: Any) -> T:
        """
        Створити новий запис.

        Приклад:
            user = await user_repo.create(
                tenant_id=tenant_id,
                telegram_id=123456,
                username="john",
            )

        session.flush() — записує в БД в рамках поточної
        транзакції, але не комітить. Це дозволяє отримати
        id об'єкта до commit().

        session.refresh() — перезавантажує об'єкт з БД,
        щоб отримати server_default значення (created_at тощо).
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    # ── UPDATE ────────────────────────────────────────────────

    async def update(
        self,
        id: uuid.UUID,
        **kwargs: Any,
    ) -> T | None:
        """
        Оновити запис за id.

        Використовуємо UPDATE ... WHERE замість завантаження
        об'єкта і зміни атрибутів — це ефективніше (один SQL
        запит замість двох).

        synchronize_session="fetch" — після UPDATE SQLAlchemy
        оновлює об'єкти в пам'яті. Потрібно для async.
        """
        await self.session.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
            .execution_options(synchronize_session="fetch")
        )
        await self.session.flush()
        return await self.get(id)

    # ── DELETE ────────────────────────────────────────────────

    async def delete(self, id: uuid.UUID) -> bool:
        """
        Видалити запис за id.

        Повертає True якщо запис існував, False якщо ні.
        """
        result = await self.session.execute(
            delete(self.model)
            .where(self.model.id == id)
            # Синхронізує Session із БД після DELETE,
            # щоб у пам'яті не залишилися вже видалені ORM-об'єкти.
            .execution_options(synchronize_session="fetch")
        )
        await self.session.flush()
        return result.rowcount > 0