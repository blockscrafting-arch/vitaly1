"""Клавиатуры для сообщений в группе (анонсы)."""
from maxapi.types import CallbackButton, LinkButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder


def announcement_keyboard(channel_url: str, bot_link_url: str | None = None) -> InlineKeyboardBuilder:
    """
    Кнопки под анонсом в группе: Открыть канал, Получить подборку в боте.

    bot_link_url: ссылка на бота (deep link или t.me-style). Если пусто,
                  используется payload для открытия лички.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        LinkButton(text="Открыть канал", url=channel_url or "https://max.ru"),
    )
    # Кнопка «Получить подборку» — открывает личку бота; по нажатию обработаем start_menu
    builder.row(
        CallbackButton(text="Получить подборку в боте", payload="start_menu"),
    )
    return builder
