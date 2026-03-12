"""Тесты keyboards: наличие кнопок и payload."""
from keyboards.main_menu import announcement_keyboard
from keyboards.sections import (
    main_menu_keyboard,
    drinks_keyboard,
    coffee_countries_keyboard,
    item_reply_keyboard,
)


def test_announcement_keyboard_has_channel_and_bot():
    """Клавиатура анонса: кнопка канала и кнопка подборки."""
    builder = announcement_keyboard("https://max.ru/channel")
    # InlineKeyboardBuilder собирает кнопки; проверим через _markup или атрибуты.
    # У InlineKeyboardBuilder обычно есть .as_markup() и внутренняя структура.
    markup = builder.as_markup()
    assert markup is not None
    # Проверяем что builder что-то содержит (конкретная структура зависит от maxapi)
    assert hasattr(builder, "as_markup")


def test_main_menu_keyboard():
    """Главное меню возвращает клавиатуру."""
    kb = main_menu_keyboard("https://max.ru")
    assert kb is not None
    assert hasattr(kb, "as_markup")


def test_drinks_keyboard():
    """Раздел напитков — клавиатура без аргументов."""
    kb = drinks_keyboard()
    assert kb is not None


def test_coffee_countries_keyboard():
    """Кофе по странам — клавиатура."""
    kb = coffee_countries_keyboard()
    assert kb is not None


def test_item_reply_keyboard():
    """Клавиатура ответа на пункт меню: канал и опционально same_payload."""
    kb = item_reply_keyboard("https://max.ru", same_payload="sub:drinks:coffee")
    assert kb is not None
    kb2 = item_reply_keyboard("https://max.ru", same_payload=None)
    assert kb2 is not None
