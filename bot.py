import logging
import pandas as pd
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext
from telegram import Update

# إعدادات اللوج
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# تحميل ملف الدرجات
df = pd.read_excel("results.xlsx")

# تنظيف الأعمدة
df.columns = df.columns.str.strip()

# تحويل عمود Number إلى نصوص
df["Number"] = df["Number"].astype(str).str.strip()


def get_result(roll_number):
    roll_number = str(roll_number).strip()
    result = df[df["Number"] == roll_number]
    if not result.empty:
        # رجّع النتيجة بدون إظهار رقم الصف
        return result.to_string(index=False)
    else:
        return "تأكد أنك أدخلت رقم الجلوس الصحيح"


def handle_message(update: Update, context: CallbackContext):
    user_input = update.message.text.strip()
    response = get_result(user_input)
    update.message.reply_text(response)


def main():
    # ضع هنا التوكن الخاص بالبوت
    
TOKEN = "429620974:AAEXymUdVhTYSYiWJ_lMhAULtitVypoQrq8"
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # التعامل مع أي رسالة نصية
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # تشغيل البوت
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
