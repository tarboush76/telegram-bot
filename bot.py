import os
import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# قراءة التوكن من Render Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")

# تحميل ملف النتائج
EXCEL_FILE = "results.xlsx"
df = pd.read_excel(EXCEL_FILE)

# دالة البداية
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً 👋! أرسل رقم الجلوس للحصول على النتيجة.")

# دالة البحث عن النتيجة
async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    if query.isdigit():  # تأكد أنه رقم
        student = df[df['رقم_الجلوس'] == int(query)]

        if not student.empty:
            name = student.iloc[0]['الاسم']
            grade = student.iloc[0]['الدرجة']
            await update.message.reply_text(f"الاسم: {name}\nالدرجة: {grade}")
        else:
            await update.message.reply_text("❌ لم يتم العثور على هذا الرقم.")
    else:
        await update.message.reply_text("📌 رجاءً أدخل رقم الجلوس فقط.")

# تشغيل البوت
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("result", result))

    app.run_polling()

if __name__ == "__main__":
    main()
