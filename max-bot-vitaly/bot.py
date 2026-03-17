"""Точка входа: контент-машина napitki133.ru — индексация, выборка, ИИ, публикация в TG и MAX по расписанию."""
import asyncio
import logging

from db import init_db
from scheduler import build_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("[bot] Запуск: инициализация БД...")
    await init_db()
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("[bot] Планировщик запущен. Ожидание слотов...")
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        scheduler.shutdown(wait=False)
        logger.info("[bot] Планировщик остановлен")


if __name__ == "__main__":
    asyncio.run(main())
