"""Планировщик: APScheduler AsyncIOScheduler, слоты по расписанию."""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import CHANNEL_DRINKS, CHANNEL_LIFHAKI, CHANNEL_TRAVEL

logger = logging.getLogger(__name__)
MISFIRE_GRACE_TIME = 3600

# Единое расписание fallback: (день, время, канал, тип_слота). ТЗ v3.0, раздел 18.
# 1 пост/день/канал. Запрещённые часы (04:00, 16:00 travel; 08:00, 20:00 lifhaki; 06:00, 18:00 drinks) исключены.
SCHEDULE_FALLBACK = [
    # travel
    ("mon", "11:30", CHANNEL_TRAVEL, "cross"),
    ("tue", "12:15", CHANNEL_TRAVEL, "main"),
    ("wed", "13:00", CHANNEL_TRAVEL, "site"),
    ("thu", "19:00", CHANNEL_TRAVEL, "radio"),
    ("fri", "11:45", CHANNEL_TRAVEL, "shop"),
    ("sat", "14:00", CHANNEL_TRAVEL, "main"),
    ("sun", "18:30", CHANNEL_TRAVEL, "main"),
    # lifhaki
    ("mon", "13:30", CHANNEL_LIFHAKI, "main"),
    ("tue", "14:15", CHANNEL_LIFHAKI, "cross"),
    ("wed", "15:00", CHANNEL_LIFHAKI, "main"),
    ("thu", "16:30", CHANNEL_LIFHAKI, "site"),
    ("fri", "17:30", CHANNEL_LIFHAKI, "shop"),
    ("sat", "12:45", CHANNEL_LIFHAKI, "main"),
    ("sun", "18:15", CHANNEL_LIFHAKI, "main"),
    # drinks
    ("mon", "12:30", CHANNEL_DRINKS, "main"),
    ("tue", "13:15", CHANNEL_DRINKS, "main"),
    ("wed", "14:30", CHANNEL_DRINKS, "site"),
    ("thu", "15:45", CHANNEL_DRINKS, "main"),
    ("fri", "12:45", CHANNEL_DRINKS, "shop"),
    ("sat", "16:15", CHANNEL_DRINKS, "main"),
    ("sun", "20:30", CHANNEL_DRINKS, "radio"),
    # AV ротация: суббота 15:00, канал по кругу
    ("sat", "15:00", "*", "rotation"),
]


def _parse_time(time_str: str) -> tuple[int, int] | None:
    try:
        part = (time_str or "").strip()
        if ":" in part:
            a, b = part.split(":", 1)
            return int(a.strip()), int(b.strip())
        return None
    except (ValueError, TypeError):
        return None


def _collect_slots_from_sheet() -> list[tuple[str, str, str, str]]:
    """Парсит лист «Расписание» в единый список (day, time, channel, slot_type)."""
    from sheets import get_schedule_from_sheet

    result: list[tuple[str, str, str, str]] = []
    try:
        sheet_schedule = get_schedule_from_sheet()
        if not sheet_schedule:
            return result
        for s in sheet_schedule:
            day = str(s.get("day") or "*").strip().lower()
            t_str = str(s.get("time") or "").strip()
            ch = str(s.get("channel") or "")
            stype = str(s.get("slot_type") or "main").strip().lower()
            if not t_str:
                continue
            # Все слоты должны иметь конкретный день (ТЗ v3.0)
            if day in ("*", ""):
                continue
            # main, shop, cross, site, radio — нужен валидный канал (не "*")
            if stype in ("main", "shop", "cross", "site", "radio") and (not ch or ch == "*"):
                continue
            result.append((day, t_str, ch, stype))
    except Exception as e:
        logger.debug("[scheduler] расписание из таблицы не загружено: %s", e)
    return result


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

    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(
        run_index_site,
        CronTrigger(hour=3, minute=30, timezone="Europe/Moscow"),
        id="index_site",
        misfire_grace_time=MISFIRE_GRACE_TIME,
    )

    JOB_FUNC = {
        "main": run_main_content_for_channel,
        "shop": run_shop_content,
        "cross": run_cross_promo,
        "site": run_site_promo,
        "radio": run_radio_promo,
        "av": run_av_rotation,
        "rotation": run_av_rotation,
    }

    all_slots = _collect_slots_from_sheet()
    if not all_slots:
        all_slots = SCHEDULE_FALLBACK

    for day, time_str, channel, slot_type in all_slots:
        func = JOB_FUNC.get(slot_type)
        if not func:
            continue
        parsed = _parse_time(time_str)
        if not parsed:
            continue
        h, m = parsed
        args = [channel] if slot_type not in ("av", "rotation") else []
        if slot_type in ("av", "rotation"):
            job_id = f"av_rotation_{day}_{time_str}"
        else:
            job_id = f"{slot_type}_{channel}_{day}_{time_str}"
        
        try:
            trigger = CronTrigger(day_of_week=day, hour=h, minute=m, timezone="Europe/Moscow")
            scheduler.add_job(
                func,
                trigger,
                args=args,
                id=job_id,
                misfire_grace_time=MISFIRE_GRACE_TIME,
            )
        except Exception as e:
            logger.warning("[scheduler] Ошибка при добавлении задачи (возможно неверный день '%s'): %s", day, e)

    content_count = sum(1 for _, _, _, st in all_slots if st not in ("av", "rotation"))
    av_count = sum(1 for _, _, _, st in all_slots if st in ("av", "rotation"))
    logger.info(
        "[scheduler] Добавлено: индексация + %s контентных слотов + %s av_rotation",
        content_count,
        av_count,
    )
    return scheduler
