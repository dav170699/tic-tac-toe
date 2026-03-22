"""
APScheduler-based scheduler.
Reads schedule config and runs the pipeline at the configured frequency.
"""
from typing import Callable

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.utils.config_loader import Config
from src.utils.logger import logger


def build_scheduler(config: Config, pipeline_fn: Callable) -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone=config.schedule.timezone)

    time_parts = config.schedule.time.split(":")
    hour = int(time_parts[0])
    minute = int(time_parts[1]) if len(time_parts) > 1 else 0

    freq = config.schedule.frequency
    if freq == "daily":
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            timezone=config.schedule.timezone,
        )
        logger.info(f"Scheduler: daily at {config.schedule.time} ({config.schedule.timezone})")

    elif freq == "weekly":
        trigger = CronTrigger(
            day_of_week=config.schedule.day_of_week,
            hour=hour,
            minute=minute,
            timezone=config.schedule.timezone,
        )
        logger.info(f"Scheduler: weekly on {config.schedule.day_of_week} at {config.schedule.time}")

    elif freq == "monthly":
        trigger = CronTrigger(
            day=config.schedule.day_of_month,
            hour=hour,
            minute=minute,
            timezone=config.schedule.timezone,
        )
        logger.info(f"Scheduler: monthly on day {config.schedule.day_of_month} at {config.schedule.time}")

    else:
        raise ValueError(f"Unknown frequency: {freq}. Use daily | weekly | monthly")

    scheduler.add_job(pipeline_fn, trigger=trigger, id="financial_agent", name="Financial Newsletter")
    return scheduler
