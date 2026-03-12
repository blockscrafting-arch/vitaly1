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
    logger.info("[bot] main: запуск, инициализация БД...")
    await init_db()
    # Прогрев кэша таблицы в потоке, чтобы первый пост не блокировал event loop
    try:
        from sheets import refresh_cache
        await asyncio.to_thread(refresh_cache)
        logger.info("[bot] main: кэш таблицы прогрет")
    except Exception as e:
        logger.warning("[bot] main: прогрев кэша таблицы не удался — %s", e)
    settings = get_settings()
    logger.info("[bot] main: конфиг загружен (channel_id=%s, group_chat_id=%s, sheet_id=%s)",
                "ok" if settings.channel_id else "пусто", "ok" if settings.group_chat_id else "пусто", "ok" if settings.google_sheet_id else "пусто")
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
        logger.info("[bot] refresh_sheets_cache_loop: фоновая задача запущена, интервал 300 с")
        while True:
            await asyncio.sleep(300)
            try:
                from sheets import refresh_cache
                await asyncio.to_thread(refresh_cache)
            except Exception as e:
                logger.warning("[bot] refresh_sheets_cache_loop: ошибка обновления кэша — %s", e, exc_info=True)

    asyncio.create_task(refresh_sheets_cache_loop())
    logger.info("[bot] Bot started, polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
