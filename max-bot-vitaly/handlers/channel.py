"""Обработка постов канала: логирование и публикация анонсов в группу."""
import logging
import time
from datetime import datetime

from maxapi.types import MessageCreated

from ai import generate_announcement
from config import get_settings
from db import add_publication
from keyboards.main_menu import announcement_keyboard
from handlers.admin import is_autopost_paused
from utils.anti_repeat import should_skip_by_antirepeat
from utils.formatter import format_announce_message
from sheets import get_cached_rules_async, add_publication_to_sheet

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
    logger.info("[channel] on_channel_post: пост канала url=%s, text_len=%s", post_url, len(post_text or ""))
    if not post_text.strip():
        logger.warning("[channel] Пост канала без текста, пропуск")
        return

    if is_autopost_paused():
        logger.info("[channel] Автопостинг приостановлен (.autopost_paused), анонс не отправляем")
        return

    settings = get_settings()
    group_chat_id = settings.group_chat_id.strip() if settings.group_chat_id else None
    if not group_chat_id:
        logger.warning("[channel] GROUP_CHAT_ID не задан в .env, анонс в группу не отправлен")
        return

    try:
        group_id = int(group_chat_id)
    except ValueError:
        logger.error("[channel] GROUP_CHAT_ID должен быть числом, получено: %r", group_chat_id)
        return

    logger.info("[channel] Запрос анонса у ИИ...")
    announcement = await generate_announcement(post_text)
    if not announcement:
        logger.warning("[channel] ИИ не вернул анонс, используем fallback (первые 200 символов поста)")
        announcement = {
            "announce": post_text[:200] + ("..." if len(post_text) > 200 else ""),
            "benefit": "Подробности в канале.",
            "question": "Что думаете по теме поста?",
            "topic": "",
            "country": "",
            "rubric": "",
        }
    topic = (announcement.get("topic") or "").strip() or None
    country = (announcement.get("country") or "").strip() or None
    rubric = (announcement.get("rubric") or "").strip() or ""

    rules = await get_cached_rules_async()
    logger.info("[channel] Правила из таблицы: %s; проверка антиповтора topic=%r, country=%r", list(rules.keys()) if rules else "пусто", topic, country)
    if await should_skip_by_antirepeat(topic=topic, country=country, rules=rules):
        logger.info("[channel] Пропуск по антиповтору (тема=%s, страна=%s) — не публикуем", topic, country)
        return

    text = format_announce_message(announcement)
    channel_url = settings.channel_url or "https://max.ru"
    builder = announcement_keyboard(channel_url, settings.bot_link_url or None)
    attachments = [builder.as_markup()]

    try:
        bot = event.message._ensure_bot()
        logger.info("[channel] Отправка сообщения в группу chat_id=%s, text_len=%s", group_id, len(text))
        await bot.send_message(
            chat_id=group_id,
            text=text,
            attachments=attachments,
        )
    except Exception as e:
        logger.exception("[channel] Ошибка отправки в группу chat_id=%s: %s", group_id, e)
        return

    ts = int(time.time())
    try:
        await add_publication(
            timestamp=ts,
            announce_text=text[:500],
            topic=topic,
            country=country,
        )
        logger.info("[channel] Запись в SQLite: topic=%r, country=%r", topic, country)
    except Exception as e:
        logger.exception("[channel] Ошибка записи в БД add_publication: %s", e)

    date_str = datetime.utcfromtimestamp(ts).strftime("%d.%m.%Y")
    try:
        add_publication_to_sheet(
            date=date_str,
            topic=topic or "",
            country=country or "",
            rubric=rubric,
            announce=announcement.get("announce", "")[:500],
            question=announcement.get("question", "")[:300],
        )
        logger.info("[channel] Строка добавлена в лист «История» Google Таблицы")
    except Exception as e:
        logger.warning("[channel] Ошибка добавления в Google Таблицу «История»: %s", e, exc_info=True)

    logger.info("[channel] Анонс успешно отправлен в группу chat_id=%s, тема=%s, страна=%s", group_id, topic, country)
