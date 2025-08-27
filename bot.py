import os
import threading
import logging
import pandas as pd
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ============ إعداد اللوج ============
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
log = logging.getLogger("results-bot")

# ============ التوكن ============
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN غير موجود. أضِفه في Secrets/Environment Variables")

# ============ ملفات الإكسل ============
EXCEL_FILES = {
    "2023": "results_2023.xlsx",
    "2024": "results_2024.xlsx",
    "2025": "results_2025.xlsx"
}

dataframes = {}
for year, filename in EXCEL_FILES.items():
    if os.path.exists(filename):
        try:
            df = pd.read_excel(filename)
            dataframes[year] = df
            log.info(f"✅ تم تحميل ملف {year}: {filename} ({len(df)} صفوف)")
        except Exception as e:
            log.error(f"❌ خطأ عند قراءة {filename}: {e}")

if not dataframes:
    raise RuntimeError("❌ لم يتم العثور على أي ملف نتائج")

# ============ دوال المساعدة ============
def get_year_from_number(number: str) -> str:
    if number.startswith("5"):
        return "2025"
    elif number.startswith("8"):
        return "2024"
    elif number.startswith("3"):
        return "2023"
    return None

def format_result(row, year):
    return f"📅 {year}\n👤 {row.iloc[0]}\n📊 {row.to_dict()}"

# ============ أوامر البوت ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بك! أرسل رقم الجلوس لمعرفة النتيجة.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.message.text.strip()
    year = get_year_from_number(q)
    if not year or year not in dataframes:
        await update.message.reply_text("❌ الرقم غير صحيح أو العام غير متاح.")
        return

    df = dataframes[year]
    result = df[df.iloc[:, 0].astype(str).str.strip() == q]
    if result.empty:
        await update.message.reply_text(f"❌ لم أجد رقم {q} في {year}.")
        return

    row = result.iloc[0]
    await update.message.reply_text(format_result(row, year))

# ============ تشغيل التليجرام ============
def run_bot():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    log.info("🤖 البوت يعمل الآن...")
    app.run_polling()

# ============ Flask Server ============
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "✅ البوت شغال على Render!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)

# ============ تشغيل الاثنين معاً ============
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    run_flask()
