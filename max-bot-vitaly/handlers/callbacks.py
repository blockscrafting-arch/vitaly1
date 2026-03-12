"""Обработка нажатий кнопок меню в личке."""
import logging

from maxapi.types import MessageCallback
from maxapi.types.updates.message_callback import MessageForCallback

from config import get_settings
from handlers.menu_texts import get_menu_text, parse_item_payload
from keyboards.sections import (
    coffee_countries_keyboard,
    drinks_keyboard,
    item_reply_keyboard,
    lifehack_keyboard,
    main_menu_keyboard,
    remote_keyboard,
    travel_keyboard,
)

logger = logging.getLogger(__name__)

# Допустимые символы в payload (защита от неожиданных данных)
_PAYLOAD_SAFE_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:.-")


def _is_safe_payload(payload: str) -> bool:
    """Проверка, что payload содержит только допустимые символы (нет инъекций/путей)."""
    return bool(payload) and len(payload) <= 256 and all(c in _PAYLOAD_SAFE_CHARS for c in payload)


async def on_callback(event: MessageCallback) -> None:
    """Роутинг по payload: main, section:*, sub:*, item:*."""
    payload = (event.callback.payload or "").strip()
    logger.debug("[callbacks] on_callback: payload=%r", payload)
    if not _is_safe_payload(payload):
        logger.warning("[callbacks] on_callback: небезопасный или пустой payload, игнор")
        await event.answer(notification="Выберите пункт меню.")
        return
    settings = get_settings()
    channel_url = settings.channel_url or "https://max.ru"

    if payload == "main" or payload == "start_menu":
        logger.info("[callbacks] payload=%s: главное меню", payload)
        text = get_menu_text("main_welcome")
        keyboard = main_menu_keyboard(channel_url)
        await event._ensure_bot().send_callback(
            callback_id=event.callback.callback_id,
            message=MessageForCallback(text=text, attachments=[keyboard.as_markup()]),
        )
        return

    if payload == "section:drinks":
        text = "Раздел: Напитки. Выберите подтему."
        keyboard = drinks_keyboard()
        await event._ensure_bot().send_callback(
            callback_id=event.callback.callback_id,
            message=MessageForCallback(text=text, attachments=[keyboard.as_markup()]),
        )
        return

    if payload == "sub:drinks:coffee":
        text = "Локальный кофе. Выберите страну."
        keyboard = coffee_countries_keyboard()
        await event._ensure_bot().send_callback(
            callback_id=event.callback.callback_id,
            message=MessageForCallback(text=text, attachments=[keyboard.as_markup()]),
        )
        return

    if payload == "section:travel":
        text = "Раздел: Путешествия. Выберите тему."
        keyboard = travel_keyboard()
        await event._ensure_bot().send_callback(
            callback_id=event.callback.callback_id,
            message=MessageForCallback(text=text, attachments=[keyboard.as_markup()]),
        )
        return

    if payload == "section:lifehack":
        text = "Раздел: Лайфхаки. Выберите тему."
        keyboard = lifehack_keyboard()
        await event._ensure_bot().send_callback(
            callback_id=event.callback.callback_id,
            message=MessageForCallback(text=text, attachments=[keyboard.as_markup()]),
        )
        return

    if payload == "section:remote":
        text = "Раздел: Для удалёнки. Выберите тему."
        keyboard = remote_keyboard()
        await event._ensure_bot().send_callback(
            callback_id=event.callback.callback_id,
            message=MessageForCallback(text=text, attachments=[keyboard.as_markup()]),
        )
        return

    if payload.startswith("item:"):
        key = parse_item_payload(payload)
        logger.info("[callbacks] payload=%s: пункт меню key=%s", payload, key)
        text = get_menu_text(key) if key else get_menu_text("direct_channel")
        # Для кофе по странам — кнопка «Ещё одну страну» ведёт обратно в sub:drinks:coffee
        same_payload = "sub:drinks:coffee" if "drinks:coffee:" in payload else None
        keyboard = item_reply_keyboard(channel_url, same_payload)
        await event._ensure_bot().send_callback(
            callback_id=event.callback.callback_id,
            message=MessageForCallback(text=text, attachments=[keyboard.as_markup()]),
        )
        return

    logger.debug("[callbacks] payload=%s: неизвестный payload, ответ «Выберите пункт меню»", payload)
    await event.answer(notification="Выберите пункт меню.")
