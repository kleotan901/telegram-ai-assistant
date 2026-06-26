import uuid

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin


class Tenant(UUIDMixin, TimestampMixin, Base):
    """
    Tenant — це клієнт (компанія або людина), яка використовує бота.

    Multi-tenant архітектура означає що один бот обслуговує
    багато незалежних клієнтів. Кожен tenant бачить тільки
    своїх користувачів і своїх тренерів.

    Приклад: компанія A і компанія B — різні tenants.
    Їх дані повністю ізольовані.
    """

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Назва компанії або проекту",
    )
    api_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        default=lambda: str(uuid.uuid4()),
        comment="Унікальний ключ для ідентифікації tenant",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Чи активний tenant",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Опис tenant (опціонально)",
    )

    # ── Relationships ─────────────────────────────────────────
    # back_populates — двостороннє посилання між моделями
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="tenant", lazy="noload"
    )
    trainers: Mapped[list["Trainer"]] = relationship(
        "Trainer", back_populates="tenant", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} name={self.name!r}>"
