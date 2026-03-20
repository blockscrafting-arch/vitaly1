"""Точка входа: контент-машина napitki133.ru — индексация, выборка, ИИ, публикация в TG и MAX по расписанию."""
import asyncio
import logging
import signal

from config import get_settings
from db import init_db
from logging_msk import configure_root_logging
from scheduler import build_scheduler

configure_root_logging(logging.INFO)
logger = logging.getLogger(__name__)


def _validate_config() -> None:
    """Проверка критичных настроек при старте."""
    settings = get_settings()
    if not (settings.telegram_bot_token and settings.telegram_bot_token.get_secret_value()):
        logger.error("[bot] V2_TELEGRAM_BOT_TOKEN не задан!")
    if not (settings.openrouter_api_key and settings.openrouter_api_key.get_secret_value()):
        logger.warning("[bot] V2_OPENROUTER_API_KEY не задан, ИИ-генерация не будет работать")

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
    _validate_config()
    _scheduler = build_scheduler()
    _scheduler.start()
    logger.info("[bot] Планировщик запущен. Ожидание слотов...")
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        if _scheduler and _scheduler.running:
            _scheduler.shutdown(wait=True)
        logger.info("[bot] Планировщик остановлен")


if __name__ == "__main__":
    asyncio.run(main())
