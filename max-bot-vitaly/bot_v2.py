"""Точка входа V2: контент-машина — индексация, выборка, ИИ, публикация в TG и MAX по расписанию."""
import asyncio
import logging

from db_v2 import init_db_v2
from scheduler_v2 import build_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("[bot_v2] Запуск V2: инициализация БД...")
    await init_db_v2()
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("[bot_v2] Планировщик запущен. Ожидание слотов...")
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        scheduler.shutdown(wait=False)
        logger.info("[bot_v2] Планировщик остановлен")


if __name__ == "__main__":
    asyncio.run(main())
