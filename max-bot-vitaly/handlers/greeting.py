"""Авто-приветствие новых участников группы."""
import logging

from maxapi.types import UserAdded

from config import get_settings
from db import set_user_greeted, was_user_greeted
from handlers.menu_texts import get_menu_text
from keyboards.sections import main_menu_keyboard

logger = logging.getLogger(__name__)

WELCOME_TEXT = """Привет! Вижу, ты присоединился к нашей группе.

У меня есть подборки по темам: напитки в разных странах, маршруты, лайфхаки для путешественников и удалёнщиков.

Выбери, что интересно:"""


async def on_user_added(event: UserAdded) -> None:
    """Новый участник в группе — отправить приветствие в личку с меню (один раз)."""
    if event.is_channel:
        logger.debug("[greeting] on_user_added: это канал, пропуск")
        return
    added_user_id = getattr(event.user, "user_id", None) if event.user else None
    if not added_user_id:
        logger.warning("[greeting] on_user_added: не удалось получить user_id, event.user=%s", event.user)
        return

    logger.info("[greeting] on_user_added: новый участник user_id=%s chat_id=%s", added_user_id, getattr(event, "chat_id", None))
    if await was_user_greeted(added_user_id):
        logger.debug("[greeting] on_user_added: user_id=%s уже приветствован, пропуск", added_user_id)
        return

    settings = get_settings()
    channel_url = settings.channel_url or "https://max.ru"
    keyboard = main_menu_keyboard(channel_url)
    bot = event.bot
    if not bot:
        logger.warning("[greeting] on_user_added: bot отсутствует, приветствие не отправлено")
        return

    try:
        await bot.send_message(
            user_id=added_user_id,
            text=WELCOME_TEXT,
            attachments=[keyboard.as_markup()],
        )
        await set_user_greeted(added_user_id, event.chat_id)
        logger.info("[greeting] Приветствие отправлено user_id=%s", added_user_id)
    except Exception as e:
        logger.warning("[greeting] Не удалось отправить приветствие user_id=%s: %s", added_user_id, e, exc_info=True)
