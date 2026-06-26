import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin


class ConversationMode(str, enum.Enum):
    """
    Режим розмови.
    AI   — відповідає штучний інтелект
    HUMAN — відповідає тренер вручну
    Переключення: AI → HUMAN відбувається автоматично
    (якщо confidence < 0.7 або need_human = true)
    або вручну тренером.

    Повернення: HUMAN → AI відбувається командою /resume
    """
    AI = "ai"
    HUMAN = "human"


class Conversation(UUIDMixin, TimestampMixin, Base):
    """
    Розмова між користувачем і ботом/тренером.

    Одна розмова = один сеанс спілкування.
    У кожного користувача може бути кілька розмов,
    але тільки одна активна (is_active=True).
    """

    __tablename__ = "conversations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mode: Mapped[ConversationMode] = mapped_column(
        Enum(ConversationMode, name="conversation_mode"),
        default=ConversationMode.AI,
        nullable=False,
        comment="Хто зараз відповідає: AI чи тренер",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Чи активна розмова",
    )

    # ── Relationships ─────────────────────────────────────────
    user: Mapped["User"] = relationship(
        "User", back_populates="conversations"
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation",
        order_by="Message.created_at",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<Conversation id={self.id} "
            f"mode={self.mode.value!r} "
            f"active={self.is_active}>"
        )
