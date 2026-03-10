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
    settings = get_settings()
    channel_url = settings.channel_url or "https://max.ru"
    text = get_menu_text("main_welcome")
    keyboard = main_menu_keyboard(channel_url)
    bot = event.bot
    if bot:
        # В личке отправляем по user_id (кто нажал Start)
        await bot.send_message(
            user_id=event.user.user_id,
            text=text,
            attachments=[keyboard.as_markup()],
        )


async def on_start_command(event: MessageCreated) -> None:
    """Команда /start — то же приветствие и меню."""
    settings = get_settings()
    channel_url = settings.channel_url or "https://max.ru"
    text = get_menu_text("main_welcome")
    keyboard = main_menu_keyboard(channel_url)
    await event.message.answer(
        text=text,
        attachments=[keyboard.as_markup()],
    )


