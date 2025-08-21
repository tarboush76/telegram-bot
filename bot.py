import os
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
from PIL import Image

TOKEN = os.getenv("BOT_TOKEN")  # ضع التوكن في بيئة التشغيل (Render/Railway)
bot = Bot(token=TOKEN)

app = Flask(__name__)

# أمر /start
def start(update: Update, context):
    update.message.reply_text("مرحباً 👋 أنا بوتك جاهز للعمل.")

# استقبال النصوص
def handle_text(update: Update, context):
    text = update.message.text
    update.message.reply_text(f"وصلني نص: {text}")

# استقبال الصور
def handle_photo(update: Update, context):
    file = update.message.photo[-1].get_file()
    file_path = "photo.jpg"
    file.download(file_path)

    try:
        img = Image.open(file_path)
        if img.format.lower() in ['jpeg', 'png']:
            update.message.reply_text("✅ الصورة صالحة (JPEG/PNG).")
        else:
            update.message.reply_text("⚠️ الصورة ليست بصيغة مدعومة.")
    except Exception as e:
        update.message.reply_text(f"خطأ في معالجة الصورة: {e}")

# إعداد التوزيع (Dispatcher)
dispatcher = Dispatcher(bot, None, workers=0)
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
dispatcher.add_handler(MessageHandler(Filters.photo, handle_photo))

# Webhook endpoint
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# نقطة البداية
@app.route("/")
def home():
    return "بوت شغال ✅"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
