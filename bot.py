import os
import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

from firestore_client import FirestoreClient
from scheduler import start_scheduler
from admin_flows import handle_admin_callback
from signals_engine import start_signals_engine
from formatters import format_ranking_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DOMAIN = os.getenv("MAGIC_LINK_DOMAIN", "https://clesscripto.app")
TOKEN_TTL_MIN = int(os.getenv("TOKEN_TTL_MIN", "10"))
ADMIN_CHAT_IDS = os.getenv("ADMIN_CHAT_IDS", "")  # comma separated
CHANNEL_CHAT_ID = os.getenv("CHANNEL_CHAT_ID", None)
TIMEZONE = os.getenv("TIMEZONE", "Europe/Lisbon")

if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN is not set")
    raise SystemExit(1)

db = FirestoreClient()  # uses GOOGLE_APPLICATION_CREDENTIALS or JSON env var

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    token = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=TOKEN_TTL_MIN)
    doc = {
        "status": "pending",
        "chat_id": chat_id,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
    }
    # create temporary token doc under telegramLinks/{token}
    await db.set_doc("telegramLinks", token, doc)
    link = f"{DOMAIN}/link?t={token}"
    await update.message.reply_text(f"Para ligar a tua conta, abre este link no teu telemóvel:\n\n{link}\n\nO link expira em {TOKEN_TTL_MIN} minutos.")

    # Start a background watcher to detect confirmation (poll fallback)
    asyncio.create_task(wait_for_confirmation(token, chat_id, context))

async def wait_for_confirmation(token: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE, timeout_sec=TOKEN_TTL_MIN*60):
    logger.info("Waiting for confirmation for token %s", token)
    start = datetime.now(timezone.utc)
    while (datetime.now(timezone.utc) - start).total_seconds() < timeout_sec:
        doc = await db.get_doc("telegramLinks", token)
        if doc:
            status = doc.get("status")
            if status == "confirmed" and doc.get("uid"):
                uid = doc.get("uid")
                # create canonical mapping telegramLinks/{uid}
                mapped = {
                    "status": "confirmed",
                    "uid": uid,
                    "chat_id": chat_id,
                    "linked_at": datetime.now(timezone.utc).isoformat(),
                }
                await db.set_doc("telegramLinks", uid, mapped)
                # delete temp token doc
                await db.delete_doc("telegramLinks", token)
                try:
                    await context.bot.send_message(chat_id=chat_id, text="✅ Conta vinculada com sucesso!")
                except Exception as e:
                    logger.exception("Failed to send confirmation DM: %s", e)
                return
        await asyncio.sleep(2)
    try:
        await context.bot.send_message(chat_id=chat_id, text="❌ O link expirou. Tenta novamente com /start.")
    except Exception:
        pass

async def ranking_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # compute top ranking from leaderboard collection
    top = await db.get_top_leaderboard(limit=10)
    text = format_ranking_message(top)
    await update.message.reply_text(text, parse_mode="Markdown")

async def meubonus_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    uid = await db.get_uid_by_chat(chat_id)
    if not uid:
        await update.message.reply_text("A tua conta não está ligada. Usa /start para vincular.")
        return
    user_doc = await db.get_doc("users", uid)
    if not user_doc:
        await update.message.reply_text("Não encontrei o teu perfil no Firestore.")
        return
    referralEarnings = user_doc.get("referralEarnings", 0)
    referralCount = user_doc.get("referralCount", 0)
    await update.message.reply_text(f"Teus bónus: {referralEarnings} STN\nReferidos: {referralCount}")

async def sinais_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args
    if not args:
        await update.message.reply_text("Uso: /sinais on|off")
        return
    opt = args[0].lower()
    uid = await db.get_uid_by_chat(chat_id)
    if not uid:
        await update.message.reply_text("A tua conta não está ligada. Usa /start para vincular.")
        return
    if opt == "on":
        await db.set_doc("userPreferences", uid, {"signals_dm": True})
        await update.message.reply_text("Receberás sinais em DM.")
    elif opt == "off":
        await db.set_doc("userPreferences", uid, {"signals_dm": False})
        await update.message.reply_text("Não receberás sinais em DM.")
    else:
        await update.message.reply_text("Uso: /sinais on|off")

async def autotrade_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args
    uid = await db.get_uid_by_chat(chat_id)
    if not uid:
        await update.message.reply_text("A tua conta não está ligada. Usa /start para vincular.")
        return
    if not args:
        await update.message.reply_text("Uso: /autotrade on <amount> | /autotrade off")
        return
    if args[0].lower() == "on":
        try:
            amount = float(args[1])
        except Exception:
            await update.message.reply_text("Especifica um valor válido. Ex: /autotrade on 500")
            return
        settings = {
            "active": True,
            "allocatedSTN": amount,
            "maxPositionPct": float(os.getenv("MAX_POSITION_PCT", "15")),
            "activated_at": datetime.now(timezone.utc).isoformat(),
            "status": "awaiting_signal",
            "consent_text": "⚠️ O autotrade é uma ferramenta automatizada ...",
            "consent_accepted_at": datetime.now(timezone.utc).isoformat(),
        }
        # IMPORTANT: in production do the transfer stnBal -> allocatedSTN in an atomic transaction
        await db.set_doc("autoTradeSettings", uid, settings)
        await update.message.reply_text(f"Autotrade ativado com {amount} STN. O bot vai propor trades por DM.")
    elif args[0].lower() == "off":
        # deactivate and close bot positions (placeholder)
        await db.update_doc("autoTradeSettings", uid, {"active": False, "deactivated_at": datetime.now(timezone.utc).isoformat()})
        await update.message.reply_text("Autotrade desativado. O bot fechará posições abertas em breve.")
    else:
        await update.message.reply_text("Uso: /autotrade on <amount> | /autotrade off")

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    admins = [int(x) for x in ADMIN_CHAT_IDS.split(",") if x.strip()]
    if chat_id not in admins:
        await update.message.reply_text("Acesso negado. Só admins podem usar este comando.")
        return
    # show admin panel (simple)
    await update.message.reply_text("Painel admin: /admin_referrals /admin_signals")

async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ranking", ranking_cmd))
    app.add_handler(CommandHandler("meubonus", meubonus_cmd))
    app.add_handler(CommandHandler("sinais", sinais_cmd))
    app.add_handler(CommandHandler("autotrade", autotrade_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^admin:"))

    # start background services
    await start_scheduler(app.bot, db)
    asyncio.create_task(start_signals_engine(app.bot, db))

    # run
    logger.info("Starting bot...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
