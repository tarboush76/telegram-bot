import telebot
import pandas as pd
from flask import Flask
import threading
import os

# التوكن من متغير البيئة
TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# تحميل الملفات (تأكد أنها مرفوعة مع الكود في Render)
data_2023 = pd.read_excel("results_2023.xlsx")
data_2024 = pd.read_excel("results_2024.xlsx")
data_2025 = pd.read_excel("results_2025.xlsx")

# توحيد الأعمدة (لو كان فيها مسافات أو اختلافات)
for df in [data_2023, data_2024, data_2025]:
    df.columns = df.columns.str.strip()
    df["id"] = df["id"].astype(str).str.strip()

# تحديد السنة من رقم الجلوس (أول رقم يحدد السنة)
def get_year_from_id(student_id: str):
    if student_id.startswith("3"):
        return results_2023, data_2023
    elif student_id.startswith("8"):
        return results_2024, data_2024
    elif student_id.startswith("5"):
        return results_2025, data_2025
    else:
        return None, None

# دالة البحث عن النتيجة
def search_result(student_id: str):
    year, df = get_year_from_id(student_id)
    if not df is None:
        result = df[df["id"] == student_id]
        if result.empty:
            return "❌ لا توجد نتيجة لهذا الرقم"
        else:
            row = result.iloc[0]
            response = f"📅 العام: {year}\n"
            for col in df.columns:
                if col == "id":
                    continue
                response += f"{col}: {row[col]}\n"
            return response
    else:
        return "❌ رقم الجلوس غير صحيح أو العام غير مدعوم"

# تعريف Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ البوت شغال على Render!"

# أوامر البوت
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "👋 أهلاً! أرسل رقم الجلوس فقط (مثال: 456789) للحصول على النتيجة.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    student_id = message.text.strip()
    reply = search_result(student_id)
    bot.reply_to(message, reply)

# تشغيل البوت
def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
