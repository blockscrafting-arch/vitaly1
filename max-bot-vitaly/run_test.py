"""Быстрый тест без ожидания расписания.

Использование:
  python run_test.py              — индексация + один основной пост (travel)
  python run_test.py main        — то же
  python run_test.py main drinks — основной пост в канал drinks
  python run_test.py shop        — один пост из магазина (travel)
  python run_test.py shop lifhaki
  python run_test.py cross       — перекрёстная реклама (travel)
  python run_test.py site        — реклама сайта (travel)
  python run_test.py radio       — реклама радио (travel)
  python run_test.py av          — ротация аудио/видео (один канал по кругу)
  python run_test.py index       — только индексация (WordPress + магазин)
"""
import asyncio
import logging
import sys

from config import CHANNEL_DRINKS, CHANNEL_LIFHAKI, CHANNEL_TRAVEL, get_settings
from db import init_db
from logging_msk import configure_root_logging
from jobs import (
    run_index_site,
    run_main_content_for_channel,
    run_shop_content,
    run_cross_promo,
    run_site_promo,
    run_radio_promo,
    run_av_rotation,
)

configure_root_logging(logging.INFO)
CHANNELS = {"travel": CHANNEL_TRAVEL, "lifhaki": CHANNEL_LIFHAKI, "drinks": CHANNEL_DRINKS}


async def main() -> None:
    get_settings()
    await init_db()
    argv = [a.lower() for a in sys.argv[1:]]
    mode = (argv[0] if argv else "main").strip()
    channel_arg = argv[1] if len(argv) > 1 else "travel"
    channel = CHANNELS.get(channel_arg, CHANNEL_TRAVEL)

    if mode in ("index",):
        print("Индексация сайта (WordPress + магазин)...")
        await run_index_site()
        print("Готово.")
        return

    if mode not in ("av", "cross", "site", "radio"):
        print("Индексация...")
        await run_index_site()

    if mode in ("main", ""):
        print(f"Один основной пост в канал {channel}...")
        await run_main_content_for_channel(channel)
    elif mode == "shop":
        print(f"Один пост из магазина в канал {channel}...")
        await run_shop_content(channel)
    elif mode == "cross":
        print(f"Перекрёстная реклама в канал {channel}...")
        await run_cross_promo(channel)
    elif mode == "site":
        print(f"Реклама сайта в канал {channel}...")
        await run_site_promo(channel)
    elif mode == "radio":
        print(f"Реклама радио в канал {channel}...")
        await run_radio_promo(channel)
    elif mode == "av":
        print("Ротация аудио/видео (один канал по кругу)...")
        await run_av_rotation()
    else:
        print(f"Неизвестный режим: {mode}. Допустимы: main, shop, cross, site, radio, av, index.")
        return
    print("Готово.")


if __name__ == "__main__":
    asyncio.run(main())
