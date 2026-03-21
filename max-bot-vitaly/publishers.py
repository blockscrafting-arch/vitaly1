"""Публикация постов в Telegram и MAX (по одному каналу за вызов)."""
import asyncio
import logging
import re

from config import get_settings

logger = logging.getLogger(__name__)

# MAX Bot API: POST /messages с query chat_id (integer) — dev.max.ru/docs-api/methods/POST/messages
# Публичный URL канала https://max.ru/id{N}_biz задаёт то же N, что ожидает API, если бот — участник чата.
# При chat.not.found сверьте ID: python list_max_chats.py
_MAX_CHANNEL_ID_RE = re.compile(r"id(\d+)", re.I)


def _normalize_max_chat_id(value: str) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    if value.isdigit():
        return int(value)
    match = _MAX_CHANNEL_ID_RE.search(value)
    if match:
        return int(match.group(1))
    return None


def _make_post_text(body: str, url: str) -> str:
    body = (body or "").strip()
    if not url:
        return body
    if url in body:
        return body
    return f"{body}\n\n{url}"


async def _retry_send(coro_factory, max_retries: int = 3, initial_delay: float = 2.0) -> bool:
    """Retry send with exponential backoff. coro_factory() returns a fresh awaitable each call."""
    delay = initial_delay
    last_exc = None
    for attempt in range(max_retries):
        try:
            await coro_factory()
            return True
        except Exception as e:
            last_exc = e
            retry_after = getattr(e, "retry_after", None)
            if retry_after is not None:
                wait = min(retry_after, 60)
                logger.warning("[publishers] Rate limit (RetryAfter), ждём %s сек", wait)
                await asyncio.sleep(wait)
                continue
            if "429" in str(e) or "retry" in str(e).lower() or "flood" in str(e).lower():
                logger.warning("[publishers] Rate limit, ждём %s сек", delay)
                await asyncio.sleep(delay)
                delay *= 2
                continue
            if attempt < max_retries - 1:
                logger.warning("[publishers] Попытка %s/%s: %s, повтор через %s сек", attempt + 1, max_retries, e, delay)
                await asyncio.sleep(delay)
                delay *= 2
            else:
                logger.exception("[publishers] Все попытки исчерпаны: %s", e)
                return False
    return False


async def publish_telegram(channel_name: str, body: str, url: str = "") -> bool:
    try:
        from aiogram import Bot
    except ImportError:
        logger.error("[publishers] aiogram не установлен")
        return False
    settings = get_settings()
    token = settings.telegram_bot_token.get_secret_value() if settings.telegram_bot_token else ""
    if not token:
        logger.warning("[publishers] TELEGRAM_BOT_TOKEN не задан (V2_)")
        return False
    channels = settings.get_telegram_channel_ids()
    chat_id = channels.get(channel_name, "").strip()
    if not chat_id:
        logger.warning("[publishers] Не задан ID канала Telegram для %s", channel_name)
        return False
    text = _make_post_text(body, url)
    if len(text) > 4096:
        text = text[:4090] + "\n\n…"
    bot = Bot(token=token)
    try:
        ok = await _retry_send(lambda: bot.send_message(chat_id=chat_id, text=text))
        if ok:
            logger.info("[publishers] Telegram: пост отправлен в канал %s", channel_name)
        return ok
    finally:
        await bot.session.close()


async def publish_max(channel_name: str, body: str, url: str = "") -> bool:
    try:
        from maxapi import Bot
    except ImportError:
        logger.error("[publishers] maxapi не установлен")
        return False
    settings = get_settings()
    token = settings.max_bot_token.get_secret_value() if settings.max_bot_token else ""
    if not token:
        logger.warning("[publishers] MAX_BOT_TOKEN не задан (V2_)")
        return False
    channels = settings.get_max_channel_ids()
    raw = channels.get(channel_name, "").strip()
    chat_id = _normalize_max_chat_id(raw)
    if chat_id is None:
        logger.warning("[publishers] Не задан или неверный ID канала MAX для %s (ожидается число или URL вида .../id123_biz)", channel_name)
        return False
    text = _make_post_text(body, url)
    if len(text) > 4096:
        text = text[:4090] + "\n\n…"
    bot = Bot(token=token)
    try:
        ok = await _retry_send(lambda: bot.send_message(chat_id=chat_id, text=text))
        if ok:
            logger.info("[publishers] MAX: пост отправлен в канал %s", channel_name)
        return ok
    finally:
        try:
            await bot.close_session()
        except Exception as close_err:
            logger.warning("[publishers] MAX: ошибка закрытия сессии — %s", close_err)


async def publish_to_both_platforms(channel_name: str, body: str, url: str = "") -> tuple[bool, bool]:
    tg_ok = await publish_telegram(channel_name, body, url)
    await asyncio.sleep(1)
    max_ok = await publish_max(channel_name, body, url)
    return (tg_ok, max_ok)
