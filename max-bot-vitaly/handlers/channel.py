"""Обработка постов канала: логирование и публикация анонсов в группу."""
import logging
import time

from maxapi.types import MessageCreated

from ai import generate_announcement
from config import get_settings
from db import add_publication
from keyboards.main_menu import announcement_keyboard
from handlers.admin import is_autopost_paused
from utils.anti_repeat import should_skip_by_antirepeat
from utils.formatter import format_announce_message

logger = logging.getLogger(__name__)


async def log_all_message_events(event: MessageCreated) -> None:
    """
    Логирует ВСЕ входящие message_created для проверки доступа к каналу.
    При публикации поста в канале у message может быть поле url (признак поста канала).
    """
    msg = event.message
    chat_id = msg.recipient.chat_id if msg.recipient else None
    user_id = msg.sender.user_id if msg.sender else None
    post_url = getattr(msg, "url", None)
    text = (msg.body.text[:300] + "...") if msg.body and msg.body.text and len(msg.body.text) > 300 else (msg.body.text if msg.body else None)

    logger.info(
        "message_created: chat_id=%s user_id=%s url=%s text_preview=%s",
        chat_id,
        user_id,
        post_url,
        repr(text)[:150] if text else None,
    )
    if post_url:
        logger.info("CHANNEL POST DETECTED: url=%s (бот получил пост канала)", post_url)


async def on_channel_post(event: MessageCreated) -> None:
    """
    Обрабатывает пост канала: генерирует анонс через ИИ и публикует в группу.
    Срабатывает только если у message есть url (признак поста канала).
    """
    msg = event.message
    post_url = getattr(msg, "url", None)
    if not post_url:
        return

    post_text = (msg.body and msg.body.text) or ""
    if not post_text.strip():
        logger.warning("Пост канала без текста, пропуск")
        return

    if is_autopost_paused():
        logger.info("Автопостинг приостановлен, анонс не отправляем")
        return

    settings = get_settings()
    group_chat_id = settings.group_chat_id.strip() if settings.group_chat_id else None
    if not group_chat_id:
        logger.warning("GROUP_CHAT_ID не задан, анонс в группу не отправлен")
        return

    try:
        group_id = int(group_chat_id)
    except ValueError:
        logger.error("GROUP_CHAT_ID должен быть числом: %s", group_chat_id)
        return

    # Антиповтор: не публиковать подряд ту же тему/страну (пока topic/country не извлекаем — всегда False)
    if await should_skip_by_antirepeat(topic=None, country=None):
        logger.info("Пропуск по антиповтору")
        return

    announcement = await generate_announcement(post_text)
    if not announcement:
        logger.warning("Не удалось сгенерировать анонс, отправка без ИИ")
        announcement = {
            "announce": post_text[:200] + ("..." if len(post_text) > 200 else ""),
            "benefit": "Подробности в канале.",
            "question": "Что думаете по теме поста?",
        }

    text = format_announce_message(announcement)
    channel_url = settings.channel_url or "https://max.ru"
    builder = announcement_keyboard(channel_url, settings.bot_link_url or None)
    attachments = [builder.as_markup()]

    bot = event.message._ensure_bot()
    await bot.send_message(
        chat_id=group_id,
        text=text,
        attachments=attachments,
    )
    await add_publication(
        timestamp=int(time.time()),
        announce_text=text[:500],
        topic=None,
        country=None,
    )
    logger.info("Анонс отправлен в группу chat_id=%s", group_id)
