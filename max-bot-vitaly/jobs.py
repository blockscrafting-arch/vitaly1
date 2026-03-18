"""Задачи планировщика: основной пост, индексация, магазин, реклама."""
import asyncio
import logging
import random
import time

from ai import fallback_text, generate_post
from config import CHANNEL_DRINKS, CHANNEL_LIFHAKI, CHANNEL_TRAVEL, get_settings
from db import (
    CONTENT_MAIN,
    CONTENT_SHOP,
    CONTENT_CROSS,
    CONTENT_SITE,
    CONTENT_RADIO,
    CONTENT_ROTATION,
    add_publication_history,
    get_catalog_for_channel,
    get_last_ad_timestamp,
    get_rotation_state,
    set_rotation_state,
)
from publishers import publish_to_both_platforms
from router import get_next_item_for_channel
from wordpress import ROTATION_TARGET
from sheets import append_history_row
from woo import get_shop_products_for_channel

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
    await asyncio.to_thread(append_history_row, url, platforms, channel_name, text[:2000])
    logger.info("[jobs] run_main_content: channel=%s url=%s tg=%s max=%s", channel_name, url[:50], tg_ok, max_ok)


async def run_shop_content(channel_name: str) -> None:
    """Один пост с товаром/книгой из магазина в заданный канал (режим Б)."""
    settings = get_settings()
    cutoff_ts = int(time.time()) - settings.shop_repeat_days * 86400
    items = await get_shop_products_for_channel(channel_name, exclude_urls_seen_after_ts=cutoff_ts, limit=200)
    if not items:
        logger.warning("[jobs] run_shop_content: нет товаров для канала %s (или все недавно публиковались), пропуск", channel_name)
        return
    _id, url, title, excerpt, _sub = random.choice(items)
    text = await generate_post(channel_name, "shop", title, excerpt or "", url)
    if not text:
        text = fallback_text(title, url)
    tg_ok, max_ok = await publish_to_both_platforms(channel_name, text, url)
    if tg_ok:
        await add_publication_history(url, "telegram", channel_name, text, CONTENT_SHOP)
    if max_ok:
        await add_publication_history(url, "max", channel_name, text, CONTENT_SHOP)
    platforms = ",".join(p for p, ok in [("telegram", tg_ok), ("max", max_ok)] if ok) or "—"
    await asyncio.to_thread(append_history_row, url, platforms, channel_name, text[:2000])
    logger.info("[jobs] run_shop_content: channel=%s url=%s tg=%s max=%s", channel_name, url[:50], tg_ok, max_ok)

# Для перекрёстной рекламы: в каком канале кого рекламируем (следующий по ротации)
CROSS_PROMO_TARGETS: dict[str, list[str]] = {
    CHANNEL_TRAVEL: [CHANNEL_LIFHAKI, CHANNEL_DRINKS],
    CHANNEL_LIFHAKI: [CHANNEL_TRAVEL, CHANNEL_DRINKS],
    CHANNEL_DRINKS: [CHANNEL_TRAVEL, CHANNEL_LIFHAKI],
}
CROSS_PROMO_NAMES = {
    CHANNEL_TRAVEL: "Путешествия",
    CHANNEL_LIFHAKI: "Лайфхаки",
    CHANNEL_DRINKS: "Напитки",
}
AD_MIN_INTERVAL_DAYS = 6


async def run_cross_promo(channel_name: str) -> None:
    """Перекрёстная реклама: нативный анонс другого канала (режим В)."""
    last_ts = await get_last_ad_timestamp(CONTENT_CROSS, channel_name)
    if last_ts and (time.time() - last_ts) < AD_MIN_INTERVAL_DAYS * 86400:
        logger.info(
            "[jobs] run_cross_promo: пропуск, реклама в %s была менее %s дней назад",
            channel_name,
            AD_MIN_INTERVAL_DAYS,
        )
        return
    targets = CROSS_PROMO_TARGETS.get(channel_name, [CHANNEL_LIFHAKI])
    key = f"cross_target_{channel_name}"
    idx = await get_rotation_state(key)
    idx = int(idx) if idx is not None else 0
    idx = idx % len(targets)
    promo_channel = targets[idx]
    await set_rotation_state(key, value_int=(idx + 1) % len(targets))
    promo_name = CROSS_PROMO_NAMES.get(promo_channel, promo_channel)
    extra = f"\n\nРекламируемый канал: {promo_name}. Напиши короткий нативный анонс, без слова «подпишитесь»."
    text = await generate_post(channel_name, "cross", promo_name, f"Канал: {promo_name}.", "", extra_context=extra)
    if not text:
        logger.warning("[jobs] run_cross_promo: ИИ не вернул текст, пропуск")
        return
    fake_url = f"cross:{promo_channel}"
    tg_ok, max_ok = await publish_to_both_platforms(channel_name, text, "")
    if tg_ok:
        await add_publication_history(fake_url, "telegram", channel_name, text, CONTENT_CROSS)
    if max_ok:
        await add_publication_history(fake_url, "max", channel_name, text, CONTENT_CROSS)
    platforms = ",".join(p for p, ok in [("telegram", tg_ok), ("max", max_ok)] if ok) or "—"
    await asyncio.to_thread(append_history_row, fake_url, platforms, channel_name, text[:2000])
    logger.info("[jobs] run_cross_promo: channel=%s promo=%s tg=%s max=%s", channel_name, promo_channel, tg_ok, max_ok)


async def run_site_promo(channel_name: str) -> None:
    """Мягкая реклама сайта napitki133.ru (режим Г)."""
    last_ts = await get_last_ad_timestamp(CONTENT_SITE, channel_name)
    if last_ts and (time.time() - last_ts) < AD_MIN_INTERVAL_DAYS * 86400:
        logger.info("[jobs] run_site_promo: пропуск, реклама сайта в %s была менее %s дней назад", channel_name, AD_MIN_INTERVAL_DAYS)
        return
    settings = get_settings()
    site_url = settings.site_url or "https://napitki133.ru"
    angle = {"travel": "путеводители, маршруты", "lifhaki": "лайфхаки, советы", "drinks": "напитки, рецепты"}.get(channel_name, "материалы сайта")
    extra = f"\n\nУгол для этого канала: {angle}. Один короткий пост про сайт."
    text = await generate_post(channel_name, "site", "napitki133.ru", f"Сайт napitki133.ru — {angle}.", site_url, extra_context=extra)
    if not text:
        text = f"napitki133.ru — {angle}.\n\n{site_url}"
    tg_ok, max_ok = await publish_to_both_platforms(channel_name, text, site_url)
    if tg_ok:
        await add_publication_history(site_url, "telegram", channel_name, text, CONTENT_SITE)
    if max_ok:
        await add_publication_history(site_url, "max", channel_name, text, CONTENT_SITE)
    platforms = ",".join(p for p, ok in [("telegram", tg_ok), ("max", max_ok)] if ok) or "—"
    await asyncio.to_thread(append_history_row, site_url, platforms, channel_name, text[:2000])
    logger.info("[jobs] run_site_promo: channel=%s tg=%s max=%s", channel_name, tg_ok, max_ok)


async def run_radio_promo(channel_name: str) -> None:
    """Реклама страницы плеера радио (режим Д)."""
    last_ts = await get_last_ad_timestamp(CONTENT_RADIO, channel_name)
    if last_ts and (time.time() - last_ts) < AD_MIN_INTERVAL_DAYS * 86400:
        logger.info("[jobs] run_radio_promo: пропуск, реклама радио в %s была менее %s дней назад", channel_name, AD_MIN_INTERVAL_DAYS)
        return
    settings = get_settings()
    radio_url = settings.radio_url or "https://napitki133.ru/internet-radio-sajta-napitki133-ru/"
    text = await generate_post(channel_name, "radio", "Радио napitki133", "Интернет-радио сайта napitki133.ru.", radio_url)
    if not text:
        text = f"Радио napitki133.ru — включай в дороге, за работой, под настроение.\n\n{radio_url}"
    tg_ok, max_ok = await publish_to_both_platforms(channel_name, text, radio_url)
    if tg_ok:
        await add_publication_history(radio_url, "telegram", channel_name, text, CONTENT_RADIO)
    if max_ok:
        await add_publication_history(radio_url, "max", channel_name, text, CONTENT_RADIO)
    platforms = ",".join(p for p, ok in [("telegram", tg_ok), ("max", max_ok)] if ok) or "—"
    await asyncio.to_thread(append_history_row, radio_url, platforms, channel_name, text[:2000])
    logger.info("[jobs] run_radio_promo: channel=%s tg=%s max=%s", channel_name, tg_ok, max_ok)


AV_ROTATION_CHANNELS = [CHANNEL_TRAVEL, CHANNEL_LIFHAKI, CHANNEL_DRINKS]
AV_ROTATION_KEY = "av_rotation_channel"


async def run_av_rotation() -> None:
    """Ротация аудио/видео: 1 раз в неделю один материал в один канал по кругу (режим Е)."""
    settings = get_settings()
    cutoff_ts = int(time.time()) - settings.repeat_interval_days * 86400
    idx = await get_rotation_state(AV_ROTATION_KEY)
    idx = int(idx) if idx is not None else 0
    idx = idx % len(AV_ROTATION_CHANNELS)
    channel_name = AV_ROTATION_CHANNELS[idx]
    rows = await get_catalog_for_channel(ROTATION_TARGET, exclude_urls_seen_after_ts=cutoff_ts, limit=200)
    if not rows:
        logger.warning("[jobs] run_av_rotation: нет материалов с content_type=rotation (аудио/видео), пропуск")
        return
    _id, url, title, excerpt, _sub = random.choice(rows)
    text = await generate_post(channel_name, "main", title, excerpt or "", url)
    if not text:
        text = fallback_text(title, url)
    tg_ok, max_ok = await publish_to_both_platforms(channel_name, text, url)
    if tg_ok:
        await add_publication_history(url, "telegram", channel_name, text, CONTENT_ROTATION)
    if max_ok:
        await add_publication_history(url, "max", channel_name, text, CONTENT_ROTATION)
    await set_rotation_state(AV_ROTATION_KEY, value_int=(idx + 1) % len(AV_ROTATION_CHANNELS))
    platforms = ",".join(p for p, ok in [("telegram", tg_ok), ("max", max_ok)] if ok) or "—"
    await asyncio.to_thread(append_history_row, url, platforms, channel_name, text[:2000])
    logger.info("[jobs] run_av_rotation: channel=%s url=%s tg=%s max=%s", channel_name, url[:50], tg_ok, max_ok)


async def run_index_site() -> None:
    from sheets import get_mapping_from_sheet
    from wordpress import index_site_to_catalog
    from woo import index_shop_to_catalog
    try:
        slug_to_channel = await asyncio.to_thread(get_mapping_from_sheet)
        n = await index_site_to_catalog(slug_to_channel=slug_to_channel)
        logger.info("[jobs] run_index_site: WordPress записей: %s", n)
        shop_n = await index_shop_to_catalog()
        logger.info("[jobs] run_index_site: магазин записей: %s", shop_n)
    except Exception:
        logger.exception("[jobs] run_index_site: ошибка индексации (WordPress/сеть/таблица)")
