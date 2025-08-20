import os
from flask import Flask, request
import telebot
TOKEN = "7216256882:AAEDFACNn9HT8VzLWuhKPsfxnbEteiqoe64"


app = Flask(__name__)

# تعريف أمر /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "✅ أهلاً! البوت شغال الآن عبر Railway 🌐")

# استقبال التحديثات من Telegram عبر Webhook
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_str = request.stream.read().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

# تعيين Webhook عند تشغيل السيرفر
@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url="https://" + os.environ.get("RAILWAY_STATIC_URL") + "/" + TOKEN)
    return "Webhook set ✅", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
