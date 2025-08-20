import telebot
import pandas as pd
import os

# التوكن يجي من Environment Variables في Railway
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("❌ لم يتم العثور على TOKEN في متغيرات البيئة. أضفه في Railway.")

bot = telebot.TeleBot(TOKEN)

# تحميل ملفات الإكسل (تأكد أنها موجودة في نفس مجلد المشروع)
try:
    data_2023 = pd.read_excel("2023.xlsx")
    data_2024 = pd.read_excel("2024.xlsx")
    data_2025 = pd.read_excel("2025.xlsx")
except Exception as e:
    print(f"⚠️ خطأ في تحميل ملفات الإكسل: {e}")
    data_2023, data_2024, data_2025 = None, None, None

# دالة البحث عن النتيجة
def search_result(student_id, year):
    if year == 2023:
        df = data_2023
    elif year == 2024:
        df = data_2024
    elif year == 2025:
        df = data_2025
    else:
        return "❌ العام غير موجود"

    if df is None:
        return "⚠️ قاعدة البيانات غير محملة بشكل صحيح."

    result = df[df["id"] == int(student_id)]
    if result.empty:
        return "❌ لا توجد نتيجة لهذا الرقم"
    else:
        return result.to_string(index=False)

# استقبال الرسائل من المستخدمين
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        parts = message.text.strip().split()
        if len(parts) == 2:
            student_id, year = parts
            reply = search_result(student_id, int(year))
        else:
            reply = "📌 أرسل الرقم والعام هكذا:\n\n807398 2024"
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, f"⚠️ حصل خطأ: {e}")

print("✅ البوت شغال الآن ...")
bot.polling(none_stop=True)
