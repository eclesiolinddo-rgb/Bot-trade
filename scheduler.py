import os
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone, time
from formatters import format_ranking_message

logger = logging.getLogger(__name__)

async def job_daily(bot, db):
    logger.info("Running daily ranking job")
    top = await db.get_top_leaderboard(limit=5)
    text = format_ranking_message(top, title="Top 5 do Dia")
    channel = os.getenv("CHANNEL_CHAT_ID")
    if channel:
        try:
            await bot.send_message(chat_id=channel, text=text, parse_mode="Markdown")
        except Exception as e:
            logger.exception("Failed to send daily ranking: %s", e)

async def job_weekly(bot, db):
    logger.info("Running weekly ranking job")
    top = await db.get_top_leaderboard(limit=10)
    text = format_ranking_message(top, title="Top 10 da Semana")
    channel = os.getenv("CHANNEL_CHAT_ID")
    if channel:
        try:
            await bot.send_message(chat_id=channel, text=text, parse_mode="Markdown")
        except Exception:
            logger.exception("Failed to send weekly ranking")

async def job_monthly(bot, db):
    logger.info("Running monthly ranking job")
    top = await db.get_top_leaderboard(limit=10)
    text = format_ranking_message(top, title="Top 10 do Mês")
    channel = os.getenv("CHANNEL_CHAT_ID")
    if channel:
        try:
            await bot.send_message(chat_id=channel, text=text, parse_mode="Markdown")
        except Exception:
            logger.exception("Failed to send monthly ranking")

async def start_scheduler(bot, db):
    scheduler = AsyncIOScheduler()
    # cron times configurable via env
    scheduler.add_job(lambda: job_daily(bot, db), "cron", hour=int(os.getenv("SCHED_DAILY_HOUR", "23")), minute=int(os.getenv("SCHED_DAILY_MIN", "55")), timezone=os.getenv("TIMEZONE", "Europe/Lisbon"))
    scheduler.add_job(lambda: job_weekly(bot, db), "cron", day_of_week=os.getenv("SCHED_WEEKLY_DAY", "sun"), hour=int(os.getenv("SCHED_WEEKLY_HOUR", "20")), minute=0, timezone=os.getenv("TIMEZONE", "Europe/Lisbon"))
    scheduler.add_job(lambda: job_monthly(bot, db), "cron", day=os.getenv("SCHED_MONTHLY_DAY", "1"), hour=int(os.getenv("SCHED_MONTHLY_HOUR", "9")), minute=0, timezone=os.getenv("TIMEZONE", "Europe/Lisbon"))
    scheduler.start()
    logger.info("Scheduler started")
