"""Scheduler for periodic jobs (rankings, other maintenance)

Uses APScheduler to schedule daily/weekly/monthly jobs. The jobs call
into FirestoreClient to compute and publish rankings or other outputs.
"""
import os
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from cless_bot.firestore_client import FirestoreClient

logger = logging.getLogger(__name__)

firestore = FirestoreClient()


async def daily_top_job():
    logger.info("Running daily top job")
    # TODO: compute top 5 from tradeFeed filtered by today and publish to channel


async def weekly_top_job():
    logger.info("Running weekly top job")


async def monthly_top_job():
    logger.info("Running monthly top job")


def start_scheduler():
    sched = AsyncIOScheduler()
    # Daily 23:55
    sched.add_job(daily_top_job, trigger="cron", hour=23, minute=55)
    # Weekly: Sunday 20:00
    sched.add_job(weekly_top_job, trigger="cron", day_of_week="sun", hour=20, minute=0)
    # Monthly: day 1 at 09:00
    sched.add_job(monthly_top_job, trigger="cron", day=1, hour=9, minute=0)
    sched.start()
    logger.info("Scheduler started")

