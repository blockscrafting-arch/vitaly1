"""Точка входа: контент-машина napitki133.ru — индексация, выборка, ИИ, публикация в TG и MAX по расписанию."""
import asyncio
import logging
import signal

from db import init_db
from scheduler import build_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_scheduler = None
_main_task: asyncio.Task | None = None


def _shutdown(_signum: int | None = None, _frame: object = None) -> None:
    global _scheduler, _main_task
    logger.info("[bot] Получен сигнал завершения, останавливаю планировщик...")
    if _scheduler:
        _scheduler.shutdown(wait=True)
        logger.info("[bot] Планировщик остановлен")
    if _main_task and not _main_task.done():
        _main_task.cancel()


async def main() -> None:
    global _scheduler, _main_task
    _main_task = asyncio.current_task()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, _shutdown)
        except (ValueError, OSError):
            pass
    logger.info("[bot] Запуск: инициализация БД...")
    await init_db()
    _scheduler = build_scheduler()
    _scheduler.start()
    logger.info("[bot] Планировщик запущен. Ожидание слотов...")
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        if _scheduler.running:
            _scheduler.shutdown(wait=True)
        logger.info("[bot] Планировщик остановлен")


if __name__ == "__main__":
    asyncio.run(main())
