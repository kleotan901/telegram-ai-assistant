import enum
import uuid

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin


class MessageRole(str, enum.Enum):
    """
    Хто написав повідомлення.

    USER    — звичайний Telegram-користувач
    AI      — відповідь від External AI API
    TRAINER — ручна відповідь тренера
    SYSTEM  — системні повідомлення (handoff, resume, тощо)
    """
    USER = "user"
    AI = "ai"
    TRAINER = "trainer"
    SYSTEM = "system"


class Message(UUIDMixin, TimestampMixin, Base):
    """
    Одне повідомлення в розмові.

    Зберігаємо всі повідомлення: від користувача, від AI,
    від тренера і системні. Це дає повну історію розмови
    і дані для навчання.

    confidence і need_human заповнюються тільки для role=AI —
    це дані з відповіді External AI API.
    """

    __tablename__ = "messages"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role"),
        nullable=False,
        comment="Хто написав повідомлення",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Текст повідомлення",
    )

    # Поля з відповіді AI API (заповнюються тільки для role=AI)
    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Впевненість AI у відповіді (0.0 - 1.0)",
    )
    need_human: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Чи просить AI передати тренеру",
    )

    # ── Relationships ─────────────────────────────────────────
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )

    def __repr__(self) -> str:
        preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return (
            f"<Message id={self.id} "
            f"role={self.role.value!r} "
            f"content={preview!r}>"
        )
