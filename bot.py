import logging
import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 🔹 ضع التوكن الخاص بك هنا
TOKEN = "PUT-YOUR-BOT-TOKEN-HERE"

# تفعيل اللوجات
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# قراءة ملف النتائج
df = pd.read_excel("results.xlsx")

# دالة البدء
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بك!\nأرسل رقم الجلوس أو اسم الطالب للحصول على النتيجة.")

# دالة البحث
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    # البحث بالرقم
    if query.isdigit():
        result = df[df["Number"].astype(str) == query]
    else:
        result = df[df["الاسم"].str.contains(query, case=False, na=False)]

    if not result.empty:
        for _, row in result.iterrows():
            reply = (
                f"📌 الاسم: {row['الاسم']}\n"
                f"🏫 المدرسة: {row['اسم المدرسة']}\n"
                f"📍 المديرية: {row['المديرية']}\n"
                f"🔢 رقم الجلوس: {row['Number']}\n\n"
                f"📖 القرآن: {row['القران']}\n"
                f"🕌 الإسلامية: {row['الاسلاميه']}\n"
                f"📝 العربي: {row['العربي']}\n"
                f"🌍 الاجتماعيات: {row['الاجتماعيات']}\n"
                f"🧮 الرياضيات: {row['الرياضيات']}\n"
                f"🔬 العلوم: {row['العلوم']}\n"
                f"💻 الإنجليزي: {row['الانجليزي']}\n\n"
                f"✅ المجموع: {row['المجموع']}\n"
                f"📊 المعدل: {row['المعدل']}\n"
                f"🎯 النتيجة: {row['النتيجة']}"
            )
            await update.message.reply_text(reply)
    else:
        await update.message.reply_text("❌ لم يتم العثور على الطالب. تأكد من كتابة الاسم أو الرقم بشكل صحيح.")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

    print("✅ البوت شغال...")
    app.run_polling()

if __name__ == "__main__":
    main()
