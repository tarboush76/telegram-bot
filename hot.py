import os
import threading
import logging
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== إعداد اللوج =====
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
log = logging.getLogger("bot")

# ===== التوكن =====
TOKEN = os.getenv("BOT_TOKEN", "429620974:AAEXymUdVhTYSYiWJ_lMhAULtitVypoQrq8")

# ===== Flask (لـ Render) =====
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ البوت شغال على Render"

# ===== Telegram Handlers =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بك! البوت شغال ✅")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.message.reply_text(f"📩 استلمت: {text}")

def run_bot():
    bot_app = Application.builder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    log.info("🚀 بدء تشغيل البوت...")
    bot_app.run_polling()

# ===== التشغيل =====
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
