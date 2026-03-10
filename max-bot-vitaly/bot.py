"""Точка входа: бот MAX для канала о напитках и путешествиях."""
import asyncio
import logging

from maxapi import Bot, Dispatcher
from maxapi.filters import Command

from config import get_settings
from db import init_db
from handlers.admin import (
    cmd_publish,
    cmd_resume,
    cmd_status,
    cmd_stop,
    cmd_test,
)
from handlers.callbacks import on_callback
from handlers.channel import log_all_message_events, on_channel_post
from handlers.greeting import on_user_added
from handlers.start import on_bot_started, on_start_command

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    await init_db()
    settings = get_settings()
    bot = Bot(settings.max_bot_token.get_secret_value())
    dp = Dispatcher()

    # Логируем все входящие сообщения; посты канала (с url) обрабатываем и пушим анонс в группу
    dp.message_created.register(log_all_message_events)
    dp.message_created.register(on_channel_post)
    dp.message_created.register(on_start_command, Command("start"))
    dp.message_created.register(cmd_publish, Command("publish"))
    dp.message_created.register(cmd_stop, Command("stop"))
    dp.message_created.register(cmd_resume, Command("resume"))
    dp.message_created.register(cmd_status, Command("status"))
    dp.message_created.register(cmd_test, Command("test"))

    dp.bot_started.register(on_bot_started)
    dp.message_callback.register(on_callback)
    dp.user_added.register(on_user_added)

    async def refresh_sheets_cache_loop() -> None:
        """Каждые 5 минут обновлять кэш Google Таблицы."""
        while True:
            await asyncio.sleep(300)
            try:
                from sheets import refresh_cache
                refresh_cache()
            except Exception as e:
                logger.debug("refresh_sheets_cache: %s", e)

    asyncio.create_task(refresh_sheets_cache_loop())
    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
