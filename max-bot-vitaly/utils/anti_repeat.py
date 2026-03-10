"""Логика антиповтора: не повторять тему/страну подряд."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from db import get_last_publications

if TYPE_CHECKING:
    pass


async def should_skip_by_antirepeat(
    topic: str | None,
    country: str | None,
    last_n: int = 10,
) -> bool:
    """
    Возвращает True, если по правилам антиповтора эту публикацию лучше пропустить
    (та же тема или та же страна что в последней записи).

    topic, country могут быть пустыми (тогда проверка только по другому полю).
    """
    last = await get_last_publications(limit=last_n)
    if not last:
        return False
    last_topic, last_country = last[0]
    if topic and last_topic and topic.strip().lower() == last_topic.strip().lower():
        return True
    if country and last_country and country.strip().lower() == last_country.strip().lower():
        return True
    return False
