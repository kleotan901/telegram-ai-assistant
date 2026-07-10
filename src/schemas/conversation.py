import uuid
from dataclasses import dataclass

from src.models.conversation import ConversationMode
from src.models.message import MessageRole
from src.models.user import UserStage


@dataclass
class AIResponse:
    """
    Відповідь від External AI API.

    Використовуємо dataclass — легший за Pydantic для
    внутрішнього використання (не потребує серіалізації).
    """
    answer: str
    confidence: float
    need_human: bool


@dataclass
class HandleMessageResult:
    """
    Результат обробки повідомлення користувача.
    Повертається з ConversationService.handle_message()
    і використовується handler-ом для відправки відповіді.
    """
    response_text: str
    mode: ConversationMode
    need_human: bool
    conversation_id: uuid.UUID
    user_id: uuid.UUID