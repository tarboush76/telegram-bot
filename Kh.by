import os
import threading
from flask import Flask
from bot import main   # نستدعي الدالة main من ملفك الحالي

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot is running!", 200

def run_bot():
    main()   # هنا نشغل البوت تبعك

if __name__ == "__main__":
    # نشغل البوت في Thread منفصل
    t = threading.Thread(target=run_bot)
    t.start()

    # Render يرسل البورت في ENV اسمه PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
