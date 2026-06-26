import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin


class UserStage(str, enum.Enum):
    """
    Стадія користувача в sales pipeline.
    str + enum.Enum — це важливо: значення зберігається як рядок
    у PostgreSQL, а не як ціле число. Читабельніше в БД.

    NEW → CONTACTED → INTERESTED → DEMO → CLIENT
    """
    NEW = "new"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    DEMO = "demo"
    CLIENT = "client"


class User(UUIDMixin, TimestampMixin, Base):
    """
    Telegram-користувач, який пише в бота.
    telegram_id — це числовий ID з Telegram API (BigInteger).
    Він унікальний в межах одного tenant.
    """

    __tablename__ = "users"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="До якого tenant належить користувач",
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,               
        nullable=False,
        index=True,
        comment="Числовий ID користувача в Telegram",
    )
    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="@username в Telegram (може бути відсутнім)",
    )
    full_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Повне ім'я з Telegram профілю",
    )
    stage: Mapped[UserStage] = mapped_column(
        Enum(UserStage, name="user_stage"),
        default=UserStage.NEW,
        nullable=False,
        comment="Поточна стадія в sales pipeline",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Чи активний користувач (не заблокував бота)",
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Час останнього повідомлення від користувача",
    )

    # ── Relationships ─────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship(
        "Tenant", back_populates="users"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="user", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<User id={self.id} "
            f"telegram_id={self.telegram_id} "
            f"stage={self.stage.value!r}>"
        )
