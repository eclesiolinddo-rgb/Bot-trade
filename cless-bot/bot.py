"""Minimal Python Telegram bot skeleton for Cless Cripto

This implements the basic linking flow described in ARQUITETURA.md:
- /start: generate token, write telegramLinks/{token} status=pending
- wait for confirmation (polling) and notify the chat when confirmed
- /ranking: read leaderboard and send top N

Requirements: configure Google credentials for the Firebase Admin SDK
and set TELEGRAM_TOKEN in environment.
"""
import os
import asyncio
import logging
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from cless_bot.firestore_client import FirestoreClient
from cless_bot.formatters import format_ranking

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_APP_URL = os.getenv("BASE_APP_URL", "https://clesscripto.app")
CONFIRM_TIMEOUT_SECONDS = int(os.getenv("CONFIRM_TIMEOUT_SECONDS", "600"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

firestore = FirestoreClient()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    token = uuid4().hex
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=CONFIRM_TIMEOUT_SECONDS)

    # create token doc
    await firestore.create_link_token(token, chat_id, now, expires_at)

    link = f"{BASE_APP_URL}/link?t={token}"
    await update.message.reply_text(
        f"Para vincular a tua conta, abre este link no teu telemóvel: {link}\n(Expira em 10 minutos)")

    # Wait for confirmation in background without blocking the handler
    async def waiter():
        try:
            uid = await firestore.wait_for_token_confirmation(token, timeout=CONFIRM_TIMEOUT_SECONDS)
            if uid:
                await context.bot.send_message(chat_id=chat_id, text="✅ Conta vinculada com sucesso!")
            else:
                await context.bot.send_message(chat_id=chat_id, text="O token expirou ou não foi confirmado.")
        except Exception as e:
            logger.exception("Error while waiting for token confirmation")
            await context.bot.send_message(chat_id=chat_id, text="Ocorreu um erro ao confirmar a conta.")

    asyncio.create_task(waiter())


async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    top = await firestore.get_top_leaderboard(limit=10)
    text = format_ranking(top)
    await update.message.reply_text(text)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Comando não reconhecido.")


def main():
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN is not set in environment")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ranking", ranking))

    # fallback for unknown commands (optional)
    # app.add_handler(MessageHandler(filters.COMMAND, unknown))

    logger.info("Starting Cless Cripto Bot")
    app.run_polling()


if __name__ == "__main__":
    main()
