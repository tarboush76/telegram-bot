
import telebot
import pandas as pd

TOKEN = "429620974:AAEXymUdVhTYSYiWJ_lMhAULtitVypoQrq8"

bot = telebot.TeleBot(TOKEN)

# تحميل ملفات النتائج
data_2023 = pd.read_excel("2023.xlsx")
data_2024 = pd.read_excel("2024.xlsx")
data_2025 = pd.read_excel("2025.xlsx")

# دالة البحث باستخدام الرقم
def search_result(student_id):
    if str(student_id).startswith("3"):
        df = data_2023
    elif str(student_id).startswith("4"):
        df = data_2024
    elif str(student_id).startswith("5"):
        df = data_2025
    else:
        return "❌ رقم الجلوس غير صحيح أو العام غير موجود"

    result = df[df["id"] == int(student_id)]
    if result.empty:
        return "❌ لا توجد نتيجة لهذا الرقم"
    else:
        return result.to_string(index=False)

# استقبال الرسائل
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        student_id = message.text.strip()
        reply = search_result(student_id)
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, f"⚠️ حصل خطأ: {e}")

print("✅ البوت شغال الآن ...")
bot.polling()