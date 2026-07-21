from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class DbSessionMiddleware(BaseMiddleware):
    """
    Middleware що додає AsyncSession до кожного update.

    Як це працює:
    1. aiogram отримує update від Telegram
    2. Перед тим як викликати handler — виконується __call__
    3. Ми відкриваємо нову сесію і кладемо в data["session"]
    4. Handler отримує session як параметр (magic injection)
    5. Після handler — сесія автоматично закривається

    Чому middleware, а не Depends як у FastAPI?
    aiogram не має Depends. Middleware — це aiogram-спосіб
    прокидати залежності у handlers.
    """

    def __init__(self, session_factory: async_sessionmaker) -> None:
        """
        session_factory — це AsyncSessionLocal з src/db/session.py
        Передаємо фабрику, а не саму сесію — бо кожен update
        повинен мати СВОЮ сесію, не спільну.
        """
        self.session_factory = session_factory
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        data — це словник що передається у кожен handler.
        Додаємо session і передаємо далі.

        async with self.session_factory() as session:
            ↑ автоматично закриє сесію після виходу з блоку
        """
        async with self.session_factory() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
