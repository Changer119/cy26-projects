from collections.abc import Callable
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


def build_scheduler(
    premarket: Callable[[], object],
    postmarket: Callable[[], object],
) -> AsyncIOScheduler:
    timezone = ZoneInfo("Asia/Shanghai")
    scheduler = AsyncIOScheduler(timezone=timezone)
    scheduler.add_job(
        premarket,
        CronTrigger(hour=7, minute=50, timezone=timezone),
        id="premarket",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=60,
    )
    scheduler.add_job(
        postmarket,
        CronTrigger(hour=18, minute=15, timezone=timezone),
        id="postmarket",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=300,
    )
    return scheduler
