import uuid

from sqlalchemy import BigInteger, Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin


class Trainer(UUIDMixin, TimestampMixin, Base):
    """
    Тренер — людина, яка відповідає замість AI
    коли confidence низький або need_human = true.

    Тренер ідентифікується за telegram_id і прив'язаний
    до конкретного tenant. Він отримує сповіщення через бота
    і відповідає командами /reply та /resume.
    """

    __tablename__ = "trainers"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
        comment="Telegram ID тренера",
    )
    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="@username тренера в Telegram",
    )
    full_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Чи активний тренер",
    )

    # ── Relationships ─────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship(
        "Tenant", back_populates="trainers"
    )

    def __repr__(self) -> str:
        return (
            f"<Trainer id={self.id} "
            f"telegram_id={self.telegram_id} "
            f"username={self.username!r}>"
        )
