"""Старт бота и главное меню."""
import logging

from maxapi.filters import Command
from maxapi.types import BotStarted, MessageCreated

from config import get_settings
from handlers.menu_texts import get_menu_text
from keyboards.sections import main_menu_keyboard

logger = logging.getLogger(__name__)


async def on_bot_started(event: BotStarted) -> None:
    """Пользователь нажал «Начать» — приветствие и главное меню."""
    user_id = event.user.user_id if event.user else None
    logger.info("[start] on_bot_started: user_id=%s", user_id)
    settings = get_settings()
    channel_url = settings.channel_url or "https://max.ru"
    text = get_menu_text("main_welcome")
    keyboard = main_menu_keyboard(channel_url)
    if user_id is None:
        logger.warning("[start] on_bot_started: event.user отсутствует, пропуск отправки")
        return
    bot = event.bot
    if bot:
        try:
            await bot.send_message(
                user_id=user_id,
                text=text,
                attachments=[keyboard.as_markup()],
            )
            logger.info("[start] on_bot_started: меню отправлено user_id=%s", user_id)
        except Exception as e:
            logger.exception("[start] on_bot_started: ошибка отправки user_id=%s — %s", user_id, e)


async def on_start_command(event: MessageCreated) -> None:
    """Команда /start — то же приветствие и меню."""
    user_id = event.message.sender.user_id if event.message and event.message.sender else None
    logger.info("[start] on_start_command: /start от user_id=%s", user_id)
    try:
        settings = get_settings()
        channel_url = settings.channel_url or "https://max.ru"
        text = get_menu_text("main_welcome")
        keyboard = main_menu_keyboard(channel_url)
        await event.message.answer(
            text=text,
            attachments=[keyboard.as_markup()],
        )
        logger.info("[start] on_start_command: меню отправлено user_id=%s", user_id)
    except Exception as e:
        logger.exception("[start] on_start_command: ошибка — %s", e)


