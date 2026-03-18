"""Планировщик: APScheduler AsyncIOScheduler, слоты по расписанию."""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import CHANNEL_DRINKS, CHANNEL_LIFHAKI, CHANNEL_TRAVEL

logger = logging.getLogger(__name__)
MISFIRE_GRACE_TIME = 3600

SCHEDULE_MAIN = [
    ("04:00", CHANNEL_TRAVEL),
    ("06:00", CHANNEL_DRINKS),
    ("08:00", CHANNEL_LIFHAKI),
    ("16:00", CHANNEL_TRAVEL),
    ("18:00", CHANNEL_DRINKS),
    ("20:00", CHANNEL_LIFHAKI),
]


SCHEDULE_SHOP = [
    ("11:30", CHANNEL_TRAVEL),
    ("12:30", CHANNEL_DRINKS),
    ("17:30", CHANNEL_LIFHAKI),
]

# Рекламные слоты по дням недели (день, время, канал, функция)
# cross: Пн travel 11:30, Вт lifhaki 13:30
# site:  Ср travel 11:30, Ср drinks 12:30, Чт lifhaki 13:30
# radio: Чт travel 19:00, Вс drinks 20:30
SCHEDULE_CROSS = [("mon", "11:30", CHANNEL_TRAVEL), ("tue", "13:30", CHANNEL_LIFHAKI)]
SCHEDULE_SITE = [("wed", "11:30", CHANNEL_TRAVEL), ("wed", "12:30", CHANNEL_DRINKS), ("thu", "13:30", CHANNEL_LIFHAKI)]
SCHEDULE_RADIO = [("thu", "19:00", CHANNEL_TRAVEL), ("sun", "20:30", CHANNEL_DRINKS)]


def _parse_time(time_str: str) -> tuple[int, int] | None:
    try:
        part = (time_str or "").strip()
        if ":" in part:
            a, b = part.split(":", 1)
            return int(a.strip()), int(b.strip())
        return None
    except (ValueError, TypeError):
        return None


def build_scheduler() -> AsyncIOScheduler:
    from jobs import (
        run_index_site,
        run_main_content_for_channel,
        run_shop_content,
        run_cross_promo,
        run_site_promo,
        run_radio_promo,
        run_av_rotation,
    )
    from sheets import get_schedule_from_sheet

    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(
        run_index_site,
        CronTrigger(hour=3, minute=30, timezone="Europe/Moscow"),
        id="index_site",
        misfire_grace_time=MISFIRE_GRACE_TIME,
    )
    main_slots = []
    shop_slots = []
    cross_slots = []
    site_slots = []
    radio_slots = []
    av_slots = []

    try:
        sheet_schedule = get_schedule_from_sheet()
        if sheet_schedule:
            for s in sheet_schedule:
                parsed = _parse_time(s.get("time") or "")
                if not parsed or not s.get("channel"):
                    continue
                day = s.get("day", "*")
                ch = s.get("channel")
                stype = s.get("slot_type", "main")
                t_str = s.get("time")
                
                if stype == "main" and day in ("*", ""):
                    main_slots.append((t_str, ch))
                elif stype == "shop" and day:
                    shop_slots.append((day, t_str, ch))
                elif stype == "cross" and day:
                    cross_slots.append((day, t_str, ch))
                elif stype == "site" and day:
                    site_slots.append((day, t_str, ch))
                elif stype == "radio" and day:
                    radio_slots.append((day, t_str, ch))
                elif stype in ("av", "rotation") and day:
                    av_slots.append((day, t_str, ch))
    except Exception as e:
        logger.debug("[scheduler] расписание из таблицы не загружено: %s", e)

    # Fallback to hardcode if sheet is empty or not loaded
    if not main_slots:
        main_slots = SCHEDULE_MAIN
    if not shop_slots:
        shop_slots = [("fri", t, ch) for t, ch in SCHEDULE_SHOP]
    if not cross_slots:
        cross_slots = SCHEDULE_CROSS
    if not site_slots:
        site_slots = SCHEDULE_SITE
    if not radio_slots:
        radio_slots = SCHEDULE_RADIO
    if not av_slots:
        av_slots = [("sat", "15:00", CHANNEL_TRAVEL)] # fallback for AV is 1 job

    for time_str, channel in main_slots:
        parsed = _parse_time(time_str)
        if not parsed:
            continue
        h, m = parsed
        scheduler.add_job(
            run_main_content_for_channel,
            CronTrigger(hour=h, minute=m, timezone="Europe/Moscow"),
            args=[channel],
            id=f"main_{channel}_{time_str}",
            misfire_grace_time=MISFIRE_GRACE_TIME,
        )

    for day, time_str, channel in shop_slots:
        parsed = _parse_time(time_str)
        if not parsed:
            continue
        h, m = parsed
        scheduler.add_job(
            run_shop_content,
            CronTrigger(day_of_week=day, hour=h, minute=m, timezone="Europe/Moscow"),
            args=[channel],
            id=f"shop_{channel}_{day}_{time_str}",
            misfire_grace_time=MISFIRE_GRACE_TIME,
        )

    for day, time_str, channel in cross_slots:
        parsed = _parse_time(time_str)
        if not parsed:
            continue
        h, m = parsed
        scheduler.add_job(
            run_cross_promo,
            CronTrigger(day_of_week=day, hour=h, minute=m, timezone="Europe/Moscow"),
            args=[channel],
            id=f"cross_{channel}_{day}_{time_str}",
            misfire_grace_time=MISFIRE_GRACE_TIME,
        )

    for day, time_str, channel in site_slots:
        parsed = _parse_time(time_str)
        if not parsed:
            continue
        h, m = parsed
        scheduler.add_job(
            run_site_promo,
            CronTrigger(day_of_week=day, hour=h, minute=m, timezone="Europe/Moscow"),
            args=[channel],
            id=f"site_{channel}_{day}_{time_str}",
            misfire_grace_time=MISFIRE_GRACE_TIME,
        )

    for day, time_str, channel in radio_slots:
        parsed = _parse_time(time_str)
        if not parsed:
            continue
        h, m = parsed
        scheduler.add_job(
            run_radio_promo,
            CronTrigger(day_of_week=day, hour=h, minute=m, timezone="Europe/Moscow"),
            args=[channel],
            id=f"radio_{channel}_{day}_{time_str}",
            misfire_grace_time=MISFIRE_GRACE_TIME,
        )

    for day, time_str, channel in av_slots:
        parsed = _parse_time(time_str)
        if not parsed:
            continue
        h, m = parsed
        scheduler.add_job(
            run_av_rotation,
            CronTrigger(day_of_week=day, hour=h, minute=m, timezone="Europe/Moscow"),
            id=f"av_rotation_{day}_{time_str}",
            misfire_grace_time=MISFIRE_GRACE_TIME,
        )

    logger.info(
        "[scheduler] Добавлено: индексация + %s основных + %s магазин + %s кросс + %s сайт + %s радио + %s av_rotation",
        len(main_slots),
        len(shop_slots),
        len(cross_slots),
        len(site_slots),
        len(radio_slots),
        len(av_slots),
    )
    return scheduler
