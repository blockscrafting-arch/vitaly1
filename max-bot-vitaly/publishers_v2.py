"""Публикация постов в Telegram и MAX (по одному каналу за вызов)."""
import asyncio
import logging

from config_v2 import get_settings_v2

logger = logging.getLogger(__name__)


def _make_post_text(body: str, url: str) -> str:
    """Склеивает текст и ссылку (если url не в конце body)."""
    body = (body or "").strip()
    if not url:
        return body
    if url in body:
        return body
    return f"{body}\n\n{url}"


async def publish_telegram(channel_name: str, body: str, url: str = "") -> bool:
    """
    Отправляет пост в канал Telegram. channel_name: travel, lifhaki, drinks.
    Возвращает True при успехе.
    """
    try:
        from aiogram import Bot
    except ImportError:
        logger.error("[publishers_v2] aiogram не установлен, публикация в Telegram недоступна")
        return False

    settings = get_settings_v2()
    token = settings.telegram_bot_token.get_secret_value() if settings.telegram_bot_token else ""
    if not token:
        logger.warning("[publishers_v2] TELEGRAM_BOT_TOKEN не задан (V2_)")
        return False

    channels = settings.get_telegram_channel_ids()
    chat_id = channels.get(channel_name, "").strip()
    if not chat_id:
        logger.warning("[publishers_v2] Не задан ID канала Telegram для %s", channel_name)
        return False

    text = _make_post_text(body, url)
    if len(text) > 4096:
        text = text[:4090] + "\n\n…"

    bot = Bot(token=token)
    try:
        await bot.send_message(chat_id=chat_id, text=text)
        logger.info("[publishers_v2] Telegram: пост отправлен в канал %s", channel_name)
        return True
    except Exception as e:
        logger.exception("[publishers_v2] Telegram: ошибка отправки в %s — %s", channel_name, e)
        return False
    finally:
        await bot.session.close()


async def publish_max(channel_name: str, body: str, url: str = "") -> bool:
    """
    Отправляет пост в канал MAX. channel_name: travel, lifhaki, drinks.
    Возвращает True при успехе.
    """
    try:
        from maxapi import Bot
    except ImportError:
        logger.error("[publishers_v2] maxapi не установлен")
        return False

    settings = get_settings_v2()
    token = settings.max_bot_token.get_secret_value() if settings.max_bot_token else ""
    if not token:
        logger.warning("[publishers_v2] MAX_BOT_TOKEN не задан (V2_)")
        return False

    channels = settings.get_max_channel_ids()
    chat_id = channels.get(channel_name, "").strip()
    if not chat_id:
        logger.warning("[publishers_v2] Не задан ID канала MAX для %s", channel_name)
        return False

    text = _make_post_text(body, url)

    bot = Bot(token=token)
    try:
        await bot.send_message(chat_id=chat_id, text=text)
        logger.info("[publishers_v2] MAX: пост отправлен в канал %s", channel_name)
        return True
    except Exception as e:
        logger.exception("[publishers_v2] MAX: ошибка отправки в %s — %s", channel_name, e)
        return False
    finally:
        try:
            await bot.close_session()
        except Exception as close_err:
            logger.warning("[publishers_v2] MAX: ошибка закрытия сессии — %s", close_err)


async def publish_to_both_platforms(channel_name: str, body: str, url: str = "") -> tuple[bool, bool]:
    """Публикует в Telegram и MAX. Возвращает (tg_ok, max_ok)."""
    tg_ok = await publish_telegram(channel_name, body, url)
    await asyncio.sleep(1)
    max_ok = await publish_max(channel_name, body, url)
    return (tg_ok, max_ok)
