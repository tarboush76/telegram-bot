import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

# توكن البوت
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

# إعداد Flask
app = Flask(__name__)

# دالة بدء
def start(update, context):
    update.message.reply_text("مرحباً 👋، البوت شغال بالويب هوك!")

# إنشاء Dispatcher
from telegram.ext import CallbackContext
dispatcher = Dispatcher(bot, None, workers=0)
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, 
                                      lambda u, c: u.message.reply_text("أهلاً بك!")))

# راوت خاص بـ Webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# الصفحة الرئيسية
@app.route("/")
def home():
    return "بوتك شغال ✅"

if __name__ == "__main__":
    # رابط الويب هوك (Render بيستخدم PORT من البيئة)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
