"""Admin flows and helpers (referral approvals, signal approvals)

Stubs for the admin flows described in ARQUITETURA.md. These functions
are intended to be called by the bot handlers when an admin presses a button.
"""
import logging

logger = logging.getLogger(__name__)


async def send_pending_referrals_to_admin(bot, admin_chat_id):
    # TODO: query referralApprovals collection and send interactive message
    await bot.send_message(admin_chat_id, "[stub] Lista de referrals pendentes")


async def handle_approve_referral(referral_id):
    # TODO: mark referral as approved in Firestore
    logger.info(f"Approved referral {referral_id}")

