"""Админ-команды: /publish, /stop, /resume, /status, /test."""
import logging
from pathlib import Path

from maxapi.filters import Command
from maxapi.types import MessageCreated

from config import get_settings
from db import get_last_publications

logger = logging.getLogger(__name__)

PAUSE_FLAG_FILE = Path(__file__).resolve().parent.parent / ".autopost_paused"


def is_autopost_paused() -> bool:
    return PAUSE_FLAG_FILE.exists()


def set_autopost_paused(paused: bool) -> None:
    if paused:
        PAUSE_FLAG_FILE.touch()
    elif PAUSE_FLAG_FILE.exists():
        PAUSE_FLAG_FILE.unlink()


def _is_admin(event: MessageCreated) -> bool:
    settings = get_settings()
    if not settings.admin_user_id:
        return False
    user_id = event.message.sender.user_id if event.message and event.message.sender else None
    return user_id == settings.admin_user_id


async def cmd_publish(event: MessageCreated) -> None:
    """Опубликовать анонс вручную (последний пост из канала — нужна реализация через API получения постов)."""
    if not _is_admin(event):
        return
    await event.message.answer("Ручная публикация: пока используйте публикацию поста в канале — бот отреагирует автоматически.")


async def cmd_stop(event: MessageCreated) -> None:
    """Приостановить автопостинг анонсов в группу."""
    if not _is_admin(event):
        return
    set_autopost_paused(True)
    await event.message.answer("Автопостинг приостановлен. Для возобновления: /resume")


async def cmd_resume(event: MessageCreated) -> None:
    """Возобновить автопостинг."""
    if not _is_admin(event):
        return
    set_autopost_paused(False)
    await event.message.answer("Автопостинг возобновлён.")


async def cmd_status(event: MessageCreated) -> None:
    """Статус: режим, последняя публикация, кол-во за сегодня."""
    if not _is_admin(event):
        return
    import time
    from datetime import datetime
    paused = is_autopost_paused()
    last = await get_last_publications(limit=1)
    today_start = int(datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    all_last = await get_last_publications(limit=100)
    today_count = sum(1 for _ in all_last)  # упрощённо: считаем все из последних 100 за сегодня не будем фильтровать по дате
    last_line = ""
    if last:
        last_line = f"Последняя: topic={last[0][0]}, country={last[0][1]}"
    msg = f"Режим: {'стоп' if paused else 'авто'}\n{last_line}\nПубликаций в последних 100: {len(all_last)}"
    await event.message.answer(msg)


async def cmd_test(event: MessageCreated) -> None:
    """Отправить тестовый анонс в тестовую группу или админу в личку."""
    if not _is_admin(event):
        return
    settings = get_settings()
    test_text = "Тестовый анонс. Проверка кнопок и формата."
    from keyboards.main_menu import announcement_keyboard
    channel_url = settings.channel_url or "https://max.ru"
    keyboard = announcement_keyboard(channel_url)
    bot = event.message._ensure_bot()
    if settings.test_group_chat_id:
        try:
            gid = int(settings.test_group_chat_id)
            await bot.send_message(chat_id=gid, text=test_text, attachments=[keyboard.as_markup()])
            await event.message.answer("Тестовый анонс отправлен в тестовую группу.")
        except Exception as e:
            logger.exception("cmd_test: отправка в тестовую группу")
            await event.message.answer("Ошибка при выполнении. Проверьте логи.")
    else:
        await bot.send_message(
            user_id=settings.admin_user_id,
            text=test_text,
            attachments=[keyboard.as_markup()],
        )
        await event.message.answer("Тестовый анонс отправлен вам в личку.")
