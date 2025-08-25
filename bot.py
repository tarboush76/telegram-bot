import os
import telebot
import pandas as pd

# استدعاء التوكن من المتغير البيئي (آمن أكثر من كتابته مباشر)
TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

# تحميل ملفات النتائج (تأكد أنها مرفوعة مع المشروع)
data_2023 = pd.read_excel("2023.xlsx")
data_2024 = pd.read_excel("2024.xlsx")
data_2025 = pd.read_excel("2025.xlsx")

# دالة البحث
def search_result(student_id: str):
    # نحدد الملف حسب أول رقم
    if student_id.startswith("3"):
        df = data_2023
    elif student_id.startswith("8"):
        df = data_2024
    elif student_id.startswith("5"):
        df = data_2025
    else:
        return "❌ الرقم غير صحيح أو غير تابع للأعوام المتاحة"

    try:
        result = df[df["id"] == int(student_id)]
    except Exception:
        return "⚠️ خطأ: تأكد أن العمود في ملف الاكسل اسمه (id)"
    
    if result.empty:
        return "❌ لا توجد نتيجة لهذا الرقم"
    else:
        return result.to_string(index=False)

# استقبال الرسائل
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    student_id = message.text.strip()
    reply = search_result(student_id)
    bot.reply_to(message, reply)

print("✅ البوت شغال الآن ...")
bot.polling(none_stop=True)
