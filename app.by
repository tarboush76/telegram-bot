from flask import Flask
import threading
import os
from bot import run_bot   # استدعاء الدالة من bot.py

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running on Render!", 200

if __name__ == "__main__":
    # شغل البوت في thread منفصل
    t = threading.Thread(target=run_bot)
    t.start()
    # Render يرسل البورت في متغير PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
