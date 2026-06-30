import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

async def notify_admins_about_referrals(bot, db):
    admins = [int(x) for x in (os.getenv("ADMIN_CHAT_IDS") or "").split(",") if x.strip()]
    # query referralApprovals collection and DM admins with approve/reject buttons
    # placeholder

async def handle_admin_callback(update, context):
    query = update.callback_query
    data = query.data  # pattern "admin:referral:approve:{id}"
    await query.answer()
    # parse and act (approve -> write to users/{uid} via admin SDK)
    await query.edit_message_text("Operação registada.")
