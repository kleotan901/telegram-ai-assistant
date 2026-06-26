"""
    ВАЖЛИВО: імпортуємо всі моделі тут.
    Alembic шукає моделі через Base.metadata.
    Якщо модель не імпортована — Alembic її не побачить і не створить таблицю.
"""


from src.models.base import Base, TimestampMixin, UUIDMixin
from src.models.tenant import Tenant
from src.models.user import User, UserStage
from src.models.conversation import Conversation, ConversationMode
from src.models.message import Message, MessageRole
from src.models.trainer import Trainer

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    "Tenant",
    "User",
    "UserStage",
    "Conversation",
    "ConversationMode",
    "Message",
    "MessageRole",
    "Trainer",
]
