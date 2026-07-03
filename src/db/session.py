from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from src.core.config import settings

# ── Engine ────────────────────────────────────────────────────
#
# create_async_engine — асинхронний двигун SQLAlchemy.
#
# echo=settings.debug — якщо DEBUG=true, в лог виводяться
# всі SQL запити. Зручно при розробці, вимикаємо в продакшні.
#
# pool_pre_ping=True — перед кожним запитом перевіряє
# чи живе з'єднання. Захист від "stale connection" після
# перезапуску PostgreSQL.

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,           # кількість з'єднань у пулі
    max_overflow=20,        # додаткові з'єднання понад pool_size
)

# ── Session Factory ───────────────────────────────────────────
#
# async_sessionmaker — фабрика для створення AsyncSession.
#
# expire_on_commit=False — після commit() об'єкти не стають
# "expired". Без цього звернення до атрибутів після commit
# викликає нові SQL запити (lazy load), що в async коді
# призводить до MissingGreenlet помилки.

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Dependency для FastAPI ────────────────────────────────────
#
# Ця функція використовується як FastAPI Dependency:
#
#   async def my_endpoint(session: AsyncSession = Depends(get_session)):
#       ...
#
# AsyncGenerator гарантує що сесія закривається навіть при
# виключенні — завдяки try/finally.

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: надає AsyncSession для одного запиту.

    Автоматично закриває сесію після завершення запиту.
    При помилці — робить rollback.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
