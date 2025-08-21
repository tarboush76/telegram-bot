import telebot
import pandas as pd

# ضع التوكن هنا مباشرة
TOKEN = "429620974:AAEXymUdVhTYSYiWJ_lMhAULtitVypoQrq8
    if df is None:
        return "❌ الرقم غير صحيح أو لا يطابق أي عام"

    try:
        result = df[df["id"] == int(student_id)]
        if result.empty:
            return "❌ لا توجد نتيجة لهذا الرقم"
        else:
            return result.to_string(index=False)
    except Exception as e:
        return f"⚠️ خطأ أثناء البحث: {e}"

# استقبال رسائل الطلاب
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    student_id = message.text.strip()
    reply = search_result(student_id)
    bot.reply_to(message, reply)

print("✅ البوت شغال الآن ...")
bot.polling()