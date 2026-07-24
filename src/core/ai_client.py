# src/core/ai_client.py — отримує URL зовнішнього API
from src.core.config import settings
import asyncio
import logging
from typing import Any, Protocol, runtime_checkable

import httpx
from src.core.exceptions import AIServiceError
from src.schemas.conversation import AIResponse

logger = logging.getLogger(__name__)

# ── Константи ─────────────────────────────────────────────────
MAX_RETRIES = 2          # кількість повторних спроб при помилці
RETRY_DELAY = 1.0        # затримка між спробами (секунди)
REQUEST_TIMEOUT = 30.0   # таймаут одного запиту (секунди)


# ── Protocol (інтерфейс) ───────────────────────────────────────
@runtime_checkable
class AIClientProtocol(Protocol):
    """
    Інтерфейс для AI клієнта.

    @runtime_checkable дозволяє перевіряти isinstance() в рантаймі:
        isinstance(client, AIClientProtocol)  # → True/False

    Будь-який клас що реалізує get_response() — відповідає протоколу.
    Не потрібно явно наслідувати цей клас.

    Використовується для type hints в ConversationService:
        def __init__(self, ai_client: AIClientProtocol): ...
    """

    async def get_response(
        self,
        user_id: str,
        message: str,
    ) -> AIResponse:
        """Отримати відповідь від AI на повідомлення користувача."""
        ...


# ── Реальний клієнт ───────────────────────────────────────────
class AIClient:
    """
    HTTP клієнт для External AI API.

    Приклад очікуваного API:
        POST /chat
        Request:  {"user_id": "123", "message": "How much?"}
        Response: {"answer": "From $29", "confidence": 0.93,
                   "need_human": false}

    Особливості:
    - httpx.AsyncClient — async HTTP, підтримує connection pooling
    - Retry логіка з затримкою між спробами
    - Timeout захищає від підвисання при повільному API
    - Кидає AIServiceError при критичних помилках
    """

    def __init__(
        self,
        api_url: str = "",
        api_key: str = "",
        timeout: float = REQUEST_TIMEOUT,
    ) -> None:
        self.api_url = api_url or settings.ai_api_url
        self.api_key = api_key or settings.ai_api_key
        self.timeout = timeout

        # httpx.AsyncClient з базовими headers
        # Один клієнт на весь lifecycle — connection pooling
        self._client = httpx.AsyncClient(
            base_url=self.api_url,
            timeout=httpx.Timeout(
                connect=5.0,     # таймаут підключення
                read=timeout,    # таймаут читання відповіді
                write=5.0,       # таймаут відправки запиту
                pool=2.0,        # таймаут отримання з'єднання з пулу
            ),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                "User-Agent": "TelegramAIAssistant/1.0",
            },
        )
        logger.info("AIClient initialized: url=%s", self.api_url)

    async def get_response(
        self,
        user_id: str,
        message: str,
    ) -> AIResponse:
        """
        Надіслати повідомлення до AI API і отримати відповідь.

        Retry логіка:
        - При помилці мережі або 5xx — повторюємо MAX_RETRIES разів
        - При 4xx (клієнтська помилка) — не повторюємо
        - Між спробами — RETRY_DELAY секунд

        Raises:
            AIServiceError: якщо всі спроби вичерпані
        """
        payload: dict[str, Any] = {
            "user_id": user_id,
            "message": message,
        }

        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                if attempt > 0:
                    logger.info(
                        "Retry attempt %d/%d for user_id=%s",
                        attempt,
                        MAX_RETRIES,
                        user_id,
                    )
                    await asyncio.sleep(RETRY_DELAY * attempt)

                response = await self._client.post(
                    "/chat",
                    json=payload,
                )

                # ── Обробка HTTP статусів ──────────────────────
                if response.status_code == 200:
                    return self._parse_response(response.json())

                elif response.status_code == 429:
                    # Rate limit — чекаємо довше
                    retry_after = int(
                        response.headers.get("Retry-After", "5")
                    )
                    logger.warning(
                        "AI API rate limited, waiting %ds",
                        retry_after,
                    )
                    await asyncio.sleep(retry_after)
                    last_error = AIServiceError(
                        f"Rate limited by AI API (429)"
                    )

                elif response.status_code >= 500:
                    # Серверна помилка — повторюємо
                    logger.warning(
                        "AI API server error: status=%d, body=%s",
                        response.status_code,
                        response.text[:200],
                    )
                    last_error = AIServiceError(
                        f"AI API server error: {response.status_code}"
                    )

                else:
                    # Клієнтська помилка (4xx) — не повторюємо
                    logger.error(
                        "AI API client error: status=%d, body=%s",
                        response.status_code,
                        response.text[:200],
                    )
                    raise AIServiceError(
                        f"AI API client error: {response.status_code}"
                    )

            except httpx.TimeoutException as e:
                logger.warning(
                    "AI API timeout on attempt %d: %s",
                    attempt + 1, e,
                )
                last_error = AIServiceError(f"AI API timeout: {e}")

            except httpx.NetworkError as e:
                logger.warning(
                    "AI API network error on attempt %d: %s",
                    attempt + 1, e,
                )
                last_error = AIServiceError(f"AI API network error: {e}")

            except AIServiceError:
                # Клієнтська помилка — пробрасуємо без retry
                raise

        # Всі спроби вичерпані
        raise AIServiceError(
            f"AI API unavailable after {MAX_RETRIES + 1} attempts. "
            f"Last error: {last_error}"
        )

    def _parse_response(self, data: dict[str, Any]) -> AIResponse:
        """
        Перетворити JSON відповідь API у внутрішній AIResponse.

        Валідуємо і нормалізуємо дані:
        - confidence обрізаємо до [0.0, 1.0]
        - need_human має бути bool
        - answer не може бути порожнім

        Захист від некоректних відповідей API —
        краще впасти тут з зрозумілою помилкою,
        ніж передати некоректні дані сервісу.
        """
        try:
            answer = str(data.get("answer", "")).strip()
            if not answer:
                raise AIServiceError("AI API returned empty answer")

            confidence = float(data.get("confidence", 0.0))
            # Нормалізуємо до [0.0, 1.0]
            confidence = max(0.0, min(1.0, confidence))

            need_human = bool(data.get("need_human", False))

            return AIResponse(
                answer=answer,
                confidence=confidence,
                need_human=need_human,
            )

        except (KeyError, TypeError, ValueError) as e:
            logger.error(
                "Failed to parse AI API response: %s. Data: %s",
                e, data,
            )
            raise AIServiceError(f"Invalid AI API response format: {e}")

    async def close(self) -> None:
        """Закрити httpx клієнт і звільнити з'єднання."""
        await self._client.aclose()
        logger.info("AIClient closed")

    async def __aenter__(self) -> "AIClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


# ── Mock клієнт для розробки і тестів ────────────────────────
class MockAIClient:
    """
    Мок AI клієнта для розробки і тестування.

    Не робить реальних HTTP запитів.
    Повертає передбачувані відповіді на основі ключових слів
    у повідомленні.

    Використання:
        # В тестах
        service = ConversationService(
            session=mock_session,
            ai_client=MockAIClient(),
            tenant_id=...,
        )

        # В розробці (поки немає реального AI API)
        # Встановити AI_API_URL=mock в .env
    """

    async def get_response(
        self,
        user_id: str,
        message: str,
    ) -> AIResponse:
        """
        Симулює відповідь AI на основі ключових слів.

        Якщо повідомлення містить "ціна" або "price" —
        повертає відповідь про ціни.
        Якщо "людина" або "менеджер" — потрібен handoff.
        Інакше — загальна відповідь.
        """
        message_lower = message.lower()

        # Симулюємо затримку мережі
        await asyncio.sleep(0.1)

        if any(word in message_lower for word in ["ціна", "price", "cost", "вартість"]):
            return AIResponse(
                answer=(
                    "Наші тарифи починаються від $29/місяць. "
                    "Є плани Basic, Pro та Enterprise. "
                    "Який план вас цікавить?"
                ),
                confidence=0.92,
                need_human=False,
            )

        if any(word in message_lower for word in ["людина", "менеджер", "оператор", "human"]):
            return AIResponse(
                answer="Зрозуміло, підключаю менеджера...",
                confidence=0.95,
                need_human=True,
            )

        if any(word in message_lower for word in ["привіт", "hello", "hi", "добрий"]):
            return AIResponse(
                answer=(
                    "Вітаю! 👋 Я розумний AI-асистент. "
                    "Чим можу допомогти?"
                ),
                confidence=0.98,
                need_human=False,
            )

        # Для незнайомих запитань — низька confidence → handoff
        if len(message) > 100:
            return AIResponse(
                answer=(
                    "Це досить детальне питання. "
                    "Дозвольте підключити нашого спеціаліста."
                ),
                confidence=0.55,   # < 0.7 → спрацює handoff
                need_human=True,
            )

        # Загальна відповідь
        return AIResponse(
            answer=(
                "Дякую за ваше запитання! "
                "Я можу розповісти більше про наші послуги. "
                "Що саме вас цікавить?"
            ),
            confidence=0.85,
            need_human=False,
        )



def create_ai_client() -> AIClientProtocol:
    """
    Фабрична функція — створює правильний клієнт
    залежно від конфігурації.

    Якщо в .env AI_API_URL=mock або порожній → MockAIClient
    Інакше → реальний AIClient

    Використання в main.py і handlers:
        ai_client = create_ai_client()
    """
    if not settings.ai_api_url or settings.ai_api_url == "mock":
        logger.info("Using MockAIClient (AI_API_URL not set or 'mock')")
        return MockAIClient()

    logger.info("Using real AIClient: url=%s", settings.ai_api_url)
    return AIClient(
        api_url=settings.ai_api_url,
        api_key=settings.ai_api_key,
    )


# Глобальний екземпляр — створюється один раз
ai_client: AIClientProtocol = create_ai_client()
