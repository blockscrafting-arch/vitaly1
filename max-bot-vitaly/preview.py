import asyncio
import logging
import random

from db import init_db, get_catalog_for_channel
from config import CHANNEL_TRAVEL, CHANNEL_LIFHAKI, CHANNEL_DRINKS, get_settings
from ai import generate_post
from router import get_next_item_for_channel
from woo import get_shop_products_for_channel
from wordpress import ROTATION_TARGET

# Отключаем лишние логи, чтобы было видно только текст
logging.basicConfig(level=logging.ERROR)

async def demo_generation():
    get_settings()
    await init_db()
    print("\n" + "="*60)
    print(" ГЕНЕРАЦИЯ ТЕКСТОВ ДЛЯ ЗАКАЗЧИКА (БЕЗ ПУБЛИКАЦИИ)")
    print("="*60 + "\n")

    # 1. ОСНОВНОЙ КОНТЕНТ
    print("1. ОСНОВНОЙ КОНТЕНТ (Канал: Путешествия)")
    item = await get_next_item_for_channel(CHANNEL_TRAVEL, mode="random", subcategory_gap=False)
    if item:
        _id, url, title, excerpt, sub = item
        text = await generate_post(CHANNEL_TRAVEL, "main", title, excerpt or "", url)
        print(f"Ссылка: {url}")
        print(f"Текст:\n{text}\n")
    else:
        print("Нет постов в базе (нужно сначала запустить индексацию)\n")

    # 2. МАГАЗИН
    print("2. МАГАЗИН (Канал: Напитки)")
    items = await get_shop_products_for_channel(CHANNEL_DRINKS, limit=50)
    if items:
        _id, url, title, excerpt, _sub = random.choice(items)
        text = await generate_post(CHANNEL_DRINKS, "shop", title, excerpt or "", url)
        print(f"Ссылка: {url}")
        print(f"Текст:\n{text}\n")
    else:
        print("Нет товаров в базе (нужно сначала запустить индексацию)\n")

    # 3. КРОСС-ПРОМО
    print("3. ПЕРЕКРЁСТНАЯ РЕКЛАМА (Лайфхаки рекламирует Путешествия)")
    extra = "\n\nРекламируемый канал: Путешествия. Напиши короткий нативный анонс, без слова «подпишитесь»."
    text = await generate_post(CHANNEL_LIFHAKI, "cross", "Путешествия", "Канал: Путешествия.", "", extra_context=extra)
    print(f"Текст:\n{text}\n")

    # 4. РЕКЛАМА САЙТА
    print("4. РЕКЛАМА САЙТА (Канал: Лайфхаки)")
    extra_site = "\n\nУгол для этого канала: лайфхаки, советы. Один короткий пост про сайт."
    text = await generate_post(CHANNEL_LIFHAKI, "site", "napitki133.ru", "Сайт napitki133.ru — лайфхаки, советы.", "https://napitki133.ru", extra_context=extra_site)
    print(f"Текст:\n{text}\n")

    # 5. РАДИО
    print("5. РАДИО (Канал: Напитки)")
    text = await generate_post(CHANNEL_DRINKS, "radio", "Радио napitki133", "Интернет-радио сайта napitki133.ru.", "https://napitki133.ru/internet-radio-sajta-napitki133-ru/")
    print(f"Текст:\n{text}\n")

    # 6. АУДИО / ВИДЕО (РОТАЦИЯ)
    print("6. АУДИО/ВИДЕО РОТАЦИЯ (Для любого канала)")
    rows = await get_catalog_for_channel(ROTATION_TARGET, limit=50)
    if rows:
        _id, url, title, excerpt, _sub = random.choice(rows)
        text = await generate_post(CHANNEL_TRAVEL, "main", title, excerpt or "", url)
        print(f"Ссылка: {url}")
        print(f"Текст:\n{text}\n")
    else:
        print("Нет аудио/видео контента в базе.\n")

    print("="*60)
    print(" Демонстрация завершена.")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(demo_generation())