import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Базовий клас для всіх SQLAlchemy моделей.
    """
    pass


class TimestampMixin:
    """
    Міксін для автоматичних полів created_at та updated_at.

    Підмішується до моделей через множинне наслідування:
      class User(TimestampMixin, Base): ...

    created_at — встановлюється один раз при INSERT
    updated_at — оновлюється при кожному UPDATE
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """
    Міксін для UUID первинного ключа.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
