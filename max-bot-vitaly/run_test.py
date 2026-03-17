"""Быстрый тест без ожидания расписания: индексация + один пост в канал travel."""
import asyncio
import logging

from config import CHANNEL_TRAVEL, get_settings
from db import init_db
from jobs import run_index_site, run_main_content_for_channel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


async def main() -> None:
    get_settings()  # проверить .env
    await init_db()
    print("Индексация сайта...")
    await run_index_site()
    print("Один пост в канал travel...")
    await run_main_content_for_channel(CHANNEL_TRAVEL)
    print("Готово.")


if __name__ == "__main__":
    asyncio.run(main())
