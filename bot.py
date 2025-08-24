import os
import telebot
import pandas as pd

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# اقرأ ملف الإكسل
df = pd.read_excel("results.xlsx")

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "أهلاً! أرسل رقم الجلوس للبحث عن نتيجتك.")

@bot.message_handler(func=lambda m: True)
def get_result(message):
    seat_no = message.text.strip()
    result = df[df['رقم الجلوس'] == int(seat_no)] if seat_no.isdigit() else None
    if result is not None and not result.empty:
        row = result.iloc[0]
        reply = f"الاسم: {row['الاسم']}\nالمجموع: {row['المجموع']}\nالنتيجة: {row['النتيجة']}"
        bot.reply_to(message, reply)
    else:
        bot.reply_to(message, "لم أجد بيانات لهذا الرقم.")

print("البوت شغال ✅")
bot.polling()
