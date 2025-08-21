import pandas as pd
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# ضع التوكن الجديد هنا 👇
TOKEN = "7216256882:AAEDFACNn9HT8VzLWuhKPsfxnbEteiqoe64"

# تحميل ملف الدرجات (تأكد أن اسم الملف مطابق الموجود بجانب bot.py)
grades = pd.read_excel("results.xlsx")

def start(update, context):
    update.message.reply_text("مرحباً 👋\nأرسل رقم جلوسك للحصول على نتيجتك.")

def get_result(update, context):
    try:
        seat_number = int(update.message.text.strip())
        row = grades.loc[grades["رقم_الجلوس"] == seat_number]

        if not row.empty:
            name = row.iloc[0]["الاسم"]
            total = row.iloc[0]["المجموع"]
            msg = f"📌 الاسم: {name}\n📊 المجموع: {total}"
        else:
            msg = "❌ رقم الجلوس غير موجود"

        update.message.reply_text(msg)
    except Exception as e:
        update.message.reply_text("⚠️ حدث خطأ، تأكد أنك أدخلت رقم جلوس صحيح.")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, get_result))

    updater.start_polling()
    print("✅ البوت يعمل الآن...")
    updater.idle()

if __name__ == "__main__":
    main()
