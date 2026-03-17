"""Задачи планировщика: основной пост, индексация."""
import asyncio
import logging

from ai import fallback_text, generate_post
from db import CONTENT_MAIN, add_publication_history
from publishers import publish_to_both_platforms
from router import get_next_item_for_channel
from sheets import append_history_row

logger = logging.getLogger(__name__)


async def run_main_content_for_channel(channel_name: str) -> None:
    item = await get_next_item_for_channel(channel_name, mode="hybrid", subcategory_gap=True)
    if not item:
        logger.warning("[jobs] run_main_content: нет материала для канала %s, пропуск", channel_name)
        return
    _id, url, title, excerpt, subcategory = item
    text = await generate_post(channel_name, "main", title, excerpt, url)
    if not text:
        text = fallback_text(title, url)
    tg_ok, max_ok = await publish_to_both_platforms(channel_name, text, url)
    if tg_ok:
        await add_publication_history(url, "telegram", channel_name, text, CONTENT_MAIN)
    if max_ok:
        await add_publication_history(url, "max", channel_name, text, CONTENT_MAIN)
    platforms = ",".join(p for p, ok in [("telegram", tg_ok), ("max", max_ok)] if ok) or "—"
    await asyncio.to_thread(append_history_row, url, platforms, channel_name, text[:300])
    logger.info("[jobs] run_main_content: channel=%s url=%s tg=%s max=%s", channel_name, url[:50], tg_ok, max_ok)


async def run_index_site() -> None:
    from sheets import get_mapping_from_sheet
    from wordpress import index_site_to_catalog
    try:
        slug_to_channel = await asyncio.to_thread(get_mapping_from_sheet)
        n = await index_site_to_catalog(slug_to_channel=slug_to_channel)
        logger.info("[jobs] run_index_site: проиндексировано записей: %s", n)
    except Exception:
        logger.exception("[jobs] run_index_site: ошибка индексации (WordPress/сеть/таблица)")
