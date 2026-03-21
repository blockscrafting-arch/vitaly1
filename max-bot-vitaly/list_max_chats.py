"""Список чатов, доступных боту MAX (для сверки V2_MAX_CHANNEL_*).

Официально: POST /messages принимает query-параметр chat_id (integer) — см. dev.max.ru.
Число из URL канала https://max.ru/id{N}_biz совпадает с этим ID, если канал тот же и бот в нём участник.

Запуск (из каталога max-bot-vitaly, с заполненным .env):
  python list_max_chats.py
"""
from __future__ import annotations

import asyncio
import sys

from config import get_settings


async def main() -> None:
    try:
        from maxapi import Bot
    except ImportError:
        print("Установите maxapi: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

    settings = get_settings()
    token = settings.max_bot_token.get_secret_value() if settings.max_bot_token else ""
    if not token:
        print("Задайте V2_MAX_BOT_TOKEN в .env", file=sys.stderr)
        sys.exit(1)

    bot = Bot(token=token)
    try:
        # API: GET /chats, до 100 за запрос
        res = await bot.get_chats(count=100)
    finally:
        try:
            await bot.close_session()
        except Exception:
            pass

    chats = res.chats or []
    if not chats:
        print("Список чатов пуст. Добавьте бота в каналы как админа и повторите.")
        return

    print(f"{'chat_id':>12}  {'status':12}  {'type':10}  title / link")
    print("-" * 100)
    for c in chats:
        title = (c.title or "—").replace("\n", " ")[:60]
        link = (c.link or "")[:80]
        extra = f"  |  {link}" if link else ""
        print(f"{c.chat_id:12d}  {str(c.status):12}  {str(c.type):10}  {title}{extra}")


if __name__ == "__main__":
    asyncio.run(main())
