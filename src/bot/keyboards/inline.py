from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_response_keyboard() -> InlineKeyboardMarkup:
    """
    Inline клавіатура з кнопками YES / NO / LATER.

    InlineKeyboardBuilder — зручний спосіб будувати
    клавіатури програмно. Альтернатива ручному
    описуванню списків кнопок.

    callback_data — це рядок що прийде в CallbackQuery
    коли користувач натисне кнопку.
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Так",
            callback_data="response:yes",
        ),
        InlineKeyboardButton(
            text="❌ Ні",
            callback_data="response:no",
        ),
        InlineKeyboardButton(
            text="⏰ Пізніше",
            callback_data="response:later",
        ),
    )

    return builder.as_markup()
