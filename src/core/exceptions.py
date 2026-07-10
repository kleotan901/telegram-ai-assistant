class AppException(Exception):
    """Базове виключення проекту."""
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class TenantNotFoundError(AppException):
    """Tenant не знайдено або неактивний."""
    pass


class UserNotFoundError(AppException):
    """Користувач не знайдений."""
    pass


class ConversationNotFoundError(AppException):
    """Активна розмова не знайдена."""
    pass


class TrainerNotFoundError(AppException):
    """Тренер не знайдений або неактивний."""
    pass


class AIServiceError(AppException):
    """Помилка при зверненні до External AI API."""
    pass
