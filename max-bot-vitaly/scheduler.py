"""Планировщик: APScheduler AsyncIOScheduler, слоты по расписанию."""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import CHANNEL_DRINKS, CHANNEL_LIFHAKI, CHANNEL_TRAVEL

logger = logging.getLogger(__name__)
MISFIRE_GRACE_TIME = 3600

SCHEDULE_MAIN = [
    ("09:00", CHANNEL_TRAVEL),
    ("10:00", CHANNEL_LIFHAKI),
    ("14:00", CHANNEL_DRINKS),
    ("19:00", CHANNEL_LIFHAKI),
    ("20:00", CHANNEL_TRAVEL),
    ("21:00", CHANNEL_DRINKS),
]


def build_scheduler() -> AsyncIOScheduler:
    from jobs import run_index_site, run_main_content_for_channel
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(
        run_index_site,
        CronTrigger(hour=4, minute=0, timezone="Europe/Moscow"),
        id="index_site",
        misfire_grace_time=MISFIRE_GRACE_TIME,
    )
    for time_str, channel in SCHEDULE_MAIN:
        h, m = map(int, time_str.split(":"))
        scheduler.add_job(
            run_main_content_for_channel,
            CronTrigger(hour=h, minute=m, timezone="Europe/Moscow"),
            args=[channel],
            id=f"main_{channel}_{time_str}",
            misfire_grace_time=MISFIRE_GRACE_TIME,
        )
    logger.info("[scheduler] Добавлено заданий: индексация + %s слотов", len(SCHEDULE_MAIN))
    return scheduler
