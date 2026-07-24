import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AIServiceError
from src.models.conversation import ConversationMode
from src.models.message import MessageRole
from src.repositories import (
    UserRepository,
    ConversationRepository,
    MessageRepository,
)
from src.schemas.conversation import AIResponse, HandleMessageResult
from src.core.ai_client import AIClientProtocol

logger = logging.getLogger(__name__)

# Поріг впевненості AI — нижче цього → human handoff
CONFIDENCE_THRESHOLD = 0.7


class ConversationService:
    """
    Головний оркестратор обробки повідомлень.

    Відповідає за:
    1. Отримання або створення User і Conversation
    2. Збереження повідомлення користувача
    3. Отримання відповіді від AI API
    4. Збереження відповіді AI
    5. Перевірку чи потрібен human handoff
    6. Повернення результату handler-у

    НЕ відповідає за:
    - Відправку повідомлень у Telegram (це handler)
    - Пряму роботу з БД (це репозиторії)
    - HTTP запити до AI (це AIClient)
    """

    def __init__(
        self,
        session: AsyncSession,
        ai_client: AIClientProtocol,
        tenant_id: uuid.UUID,
    ) -> None:
        self.session = session
        self.ai_client = ai_client
        self.tenant_id = tenant_id

        # Всі репозиторії ділять одну сесію → одна транзакція
        self.user_repo = UserRepository(session)
        self.conv_repo = ConversationRepository(session)
        self.msg_repo = MessageRepository(session)

    async def handle_message(
        self,
        telegram_id: int,
        text: str,
        username: str | None = None,
        full_name: str | None = None,
    ) -> HandleMessageResult:
        """
        Обробити вхідне повідомлення від Telegram-користувача.

        Flow:
        1. get_or_create User
        2. get_or_create active Conversation
        3. Якщо conversation.mode == HUMAN → не чіпаємо AI,
           просто зберігаємо повідомлення
        4. Якщо mode == AI → питаємо AI API
        5. Перевіряємо confidence і need_human
        6. Зберігаємо відповідь
        7. Повертаємо результат
        """
        # ── Крок 1: User ──────────────────────────────────────
        user, is_new = await self.user_repo.get_or_create(
            telegram_id=telegram_id,
            tenant_id=self.tenant_id,
            username=username,
            full_name=full_name,
        )

        if is_new:
            logger.info(
                "New user registered: telegram_id=%s tenant=%s",
                telegram_id,
                self.tenant_id,
            )

        # ── Крок 2: Conversation ──────────────────────────────
        conversation, _ = await self.conv_repo.get_or_create_active(
            user_id=user.id,
            tenant_id=self.tenant_id,
        )

        # ── Крок 3: Зберігаємо повідомлення користувача ───────
        await self.msg_repo.create_message(
            conversation_id=conversation.id,
            tenant_id=self.tenant_id,
            role=MessageRole.USER,
            content=text,
        )

        # Оновлюємо last_seen
        await self.user_repo.update_last_seen(user.id)

        # ── Крок 4: HUMAN mode — AI не питаємо ────────────────
        if conversation.mode == ConversationMode.HUMAN:
            logger.info(
                "Conversation %s in HUMAN mode, skipping AI",
                conversation.id,
            )
            return HandleMessageResult(
                response_text="",           # handler не відправить нічого
                mode=ConversationMode.HUMAN,
                need_human=False,
                conversation_id=conversation.id,
                user_id=user.id,
            )

        # ── Крок 5: AI mode — питаємо AI API ──────────────────
        try:
            ai_response: AIResponse = await self.ai_client.get_response(
                user_id=str(user.id),
                message=text,
            )
        except AIServiceError as e:
            logger.error("AI API error: %s", e.message)
            # При помилці AI — fallback повідомлення
            return HandleMessageResult(
                response_text=(
                    "Вибачте, виникла технічна помилка. "
                    "Наш менеджер зв'яжеться з вами найближчим часом."
                ),
                mode=ConversationMode.HUMAN,
                need_human=True,
                conversation_id=conversation.id,
                user_id=user.id,
            )

        # ── Крок 6: Зберігаємо відповідь AI ───────────────────
        await self.msg_repo.create_message(
            conversation_id=conversation.id,
            tenant_id=self.tenant_id,
            role=MessageRole.AI,
            content=ai_response.answer,
            confidence=ai_response.confidence,
            need_human=ai_response.need_human,
        )

        # ── Крок 7: Перевіряємо чи потрібен handoff ───────────
        needs_handoff = (
            ai_response.confidence < CONFIDENCE_THRESHOLD
            or ai_response.need_human
        )

        if needs_handoff:
            # Перемикаємо conversation в HUMAN mode
            await self.conv_repo.set_mode(
                conversation.id,
                ConversationMode.HUMAN,
            )
            logger.info(
                "Handoff triggered for conversation %s "
                "(confidence=%.2f, need_human=%s)",
                conversation.id,
                ai_response.confidence,
                ai_response.need_human,
            )

        return HandleMessageResult(
            response_text=ai_response.answer,
            mode=(
                ConversationMode.HUMAN
                if needs_handoff
                else ConversationMode.AI
            ),
            need_human=needs_handoff,
            conversation_id=conversation.id,
            user_id=user.id,
        )

    async def get_conversation_history(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
    ) -> list:
        """Отримати історію розмови для контексту."""
        conversation = await self.conv_repo.get_active(
            user_id=user_id,
            tenant_id=self.tenant_id,
        )
        if not conversation:
            return []

        return await self.msg_repo.get_history(
            conversation_id=conversation.id,
            limit=limit,
        )
