"""Демо генерации текстов без публикации (ТЗ v3.0).

Повторяет вызовы generate_post так же, как jobs.py (режимы main/shop/cross/site/radio/rotation),
но не вызывает publishers. Нужны: .env с V2_OPENROUTER_API_KEY, заполненный bot.db (индексация).

Запуск: python preview.py
"""
import asyncio
import logging
import time

from db import init_db, get_catalog_for_channel
from config import CHANNEL_TRAVEL, CHANNEL_LIFHAKI, CHANNEL_DRINKS, get_settings
from ai import generate_post
from router import get_next_item_for_channel
from woo import get_shop_products_for_channel
from wordpress import ROTATION_TARGET
from jobs import _get_repeat_interval_days, _get_shop_repeat_days

# Отключаем лишние логи, чтобы было видно только текст
logging.basicConfig(level=logging.ERROR)


async def demo_generation() -> None:
    settings = get_settings()
    await init_db()
    site_url = settings.site_url or "https://napitki133.ru"
    radio_url = settings.radio_url or "https://napitki133.ru/internet-radio-sajta-napitki133-ru/"

    print("\n" + "=" * 60)
    print(" ГЕНЕРАЦИЯ ТЕКСТОВ ДЛЯ ЗАКАЗЧИКА (БЕЗ ПУБЛИКАЦИИ) — как в jobs.py")
    print("=" * 60 + "\n")

    # 1. ОСНОВНОЙ КОНТЕНТ — как run_main_content_for_channel (hybrid + subcategory_gap)
    print("1. ОСНОВНОЙ КОНТЕНТ (Канал: Путешествия, hybrid + subcategory_gap)")
    item = await get_next_item_for_channel(CHANNEL_TRAVEL, mode="hybrid", subcategory_gap=True)
    if item:
        _id, url, title, excerpt, _sub = item
        text = await generate_post(CHANNEL_TRAVEL, "main", title, excerpt or "", url)
        print(f"Ссылка: {url}")
        print(f"Текст:\n{text}\n")
    else:
        print("Нет постов в базе (нужно сначала запустить индексацию)\n")

    # 2. МАГАЗИН — как run_shop_content (Sheet/config + order_by_random)
    print("2. МАГАЗИН (Канал: Напитки, как run_shop_content)")
    cutoff_shop = int(time.time()) - _get_shop_repeat_days() * 86400
    items = await get_shop_products_for_channel(
        CHANNEL_DRINKS,
        exclude_urls_seen_after_ts=cutoff_shop,
        limit=1,
        order_by_random=True,
    )
    if items:
        _id, url, title, excerpt, _sub = items[0]
        text = await generate_post(CHANNEL_DRINKS, "shop", title, excerpt or "", url)
        print(f"Ссылка: {url}")
        print(f"Текст:\n{text}\n")
    else:
        print("Нет товаров в базе (нужно сначала запустить индексацию магазина)\n")

    # 3. КРОСС-ПРОМО — как run_cross_promo
    print("3. ПЕРЕКРЁСТНАЯ РЕКЛАМА (Лайфхаки → Путешествия)")
    extra = "\n\nРекламируемый канал: Путешествия. Напиши короткий нативный анонс, без слова «подпишитесь»."
    text = await generate_post(CHANNEL_LIFHAKI, "cross", "Путешествия", "Канал: Путешествия.", "", extra_context=extra)
    print(f"Текст:\n{text}\n")

    # 4. РЕКЛАМА САЙТА — как run_site_promo (PROMPTS_SITE + угол из jobs)
    print("4. РЕКЛАМА САЙТА (Канал: Лайфхаки, site_* промпт + extra как в jobs)")
    angle = {"travel": "путеводители, маршруты", "lifhaki": "лайфхаки, советы", "drinks": "напитки, рецепты"}.get(
        CHANNEL_LIFHAKI, "материалы сайта"
    )
    extra_site = f"\n\nУгол для этого канала: {angle}. Один короткий пост про сайт."
    text = await generate_post(
        CHANNEL_LIFHAKI,
        "site",
        "napitki133.ru",
        f"Сайт napitki133.ru — {angle}.",
        site_url,
        extra_context=extra_site,
    )
    print(f"Текст:\n{text}\n")

    # 5. РАДИО — как run_radio_promo
    print("5. РАДИО (Канал: Напитки, radio_url из .env/config)")
    text = await generate_post(
        CHANNEL_DRINKS,
        "radio",
        "Радио napitki133",
        "Интернет-радио сайта napitki133.ru.",
        radio_url,
    )
    print(f"Текст:\n{text}\n")

    # 6. AV РОТАЦИЯ — как run_av_rotation (rotation + cutoff + random)
    print("6. АУДИО/ВИДЕО РОТАЦИЯ (канал travel для промпта rotation_travel, выборка как в jobs)")
    cutoff_rot = int(time.time()) - _get_repeat_interval_days() * 86400
    rows = await get_catalog_for_channel(
        ROTATION_TARGET,
        exclude_urls_seen_after_ts=cutoff_rot,
        limit=1,
        order_by_random=True,
    )
    if rows:
        _id, url, title, excerpt, _sub = rows[0]
        text = await generate_post(CHANNEL_TRAVEL, "rotation", title, excerpt or "", url)
        print(f"Ссылка: {url}")
        print(f"Текст:\n{text}\n")
    else:
        print("Нет аудио/видео контента в базе (или всё в окне повтора).\n")

    print("=" * 60)
    print(" Демонстрация завершена.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(demo_generation())
