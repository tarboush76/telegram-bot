import os
import logging
from flask import Flask, request
import requests
import pandas as pd

# إعداد اللوجات
logging.basicConfig(level=logging.INFO)

# جلب التوكن من Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ لازم تضيف BOT_TOKEN في Environment Variables داخل Render")

# رابط API
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# إعداد Flask
app = Flask(__name__)

# تحميل ملف الاكسل
EXCEL_FILE = "grades.xlsx"   # لازم ترفعه مع الملفات
df = pd.read_excel(EXCEL_FILE)

# الصفحة الرئيسية
@app.route("/")
def home():
    return "✅ البوت شغال على Render!"

# استقبال رسائل تيليجرام
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "").strip()

        # البحث في ملف الدرجات
        result = df[df['name'].str.contains(text, case=False, na=False)]

        if not result.empty:
            # نعرض أول صف مطابق
            student = result.iloc[0]
            reply = f"📊 النتيجة:\n\n👤 الاسم: {student['name']}\n📌 الدرجة: {student['grade']}"
        else:
            reply = "⚠️ لم أجد أي طالب بهذا الاسم."

        # إرسال الرد
        requests.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": reply
        })

    return {"ok": True}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
