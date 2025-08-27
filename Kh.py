import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد اللوج
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("results-bot")

# التوكن
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN غير موجود")

# رابط Render (غيره حسب رابط مشروعك)
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook/{TOKEN}"

# إعداد Flask
app = Flask(__name__)
telegram_app = Application.builder().token(TOKEN).build()

# أوامر البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بك! البوت شغال ✅")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📩 استلمت: {update.message.text}")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# Flask route
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    telegram_app.update_queue.put_nowait(update)
    return "ok"

@app.route("/")
def index():
    return "🤖 البوت شغال"

# عند تشغيل السيرفر
if __name__ == "__main__":
    # ضبط الـ webhook
    import asyncio
    async def set_webhook():
        await telegram_app.bot.set_webhook(WEBHOOK_URL)
        log.info(f"✅ Webhook set to {WEBHOOK_URL}")
    asyncio.run(set_webhook())

    # تشغيل Flask
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
