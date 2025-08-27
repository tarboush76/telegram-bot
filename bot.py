import os
import logging
import pandas as pd
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ============ إعداد اللوج ============
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("results-bot")

# ============ التوكن ============
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN غير موجود. أضِفه في Secrets")

# ============ رابط Webhook ============
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook/{TOKEN}"

# ============ تحميل ملفات الإكسل ============
EXCEL_FILES = {
    "2023": "results_2023.xlsx",
    "2024": "results_2024.xlsx",
    "2025": "results_2025.xlsx"
}

dataframes = {}
for year, filename in EXCEL_FILES.items():
    try:
        if os.path.exists(filename):
            df = pd.read_excel(filename)
            dataframes[year] = df
            log.info(f"✅ تم تحميل ملف {year}: {filename} ({len(df)} صف)")
        else:
            log.warning(f"⚠️ الملف {filename} غير موجود")
    except Exception as e:
        log.error(f"❌ خطأ في تحميل ملف {filename}: {e}")

if not dataframes:
    raise RuntimeError("❌ لم يتم العثور على أي ملف نتائج")

# ============ دوال البحث ============
def get_year_from_number(number: str) -> str:
    if number.startswith("5"):
        return "2025"
    elif number.startswith("8"):
        return "2024"
    elif number.startswith("3"):
        return "2023"
    return None

def search_by_number(q: str):
    year = get_year_from_number(q)
    if not year or year not in dataframes:
        return f"❌ رقم الجلوس {q} غير مرتبط بأي ملف"
    df = dataframes[year]
    result = df[df[df.columns[0]].astype(str).str.strip() == q]
    if result.empty:
        return f"❌ لم أجد رقم الجلوس {q} في نتائج {year}"
    return result.to_string(index=False)

def search_by_name(q: str):
    results = []
    for year, df in dataframes.items():
        mask = df[df.columns[1]].astype(str).str.contains(q, case=False, na=False)
        matches = df[mask]
        if not matches.empty:
            results.append(f"📅 {year}\n" + matches.to_string(index=False))
    return "\n\n".join(results) if results else f"❌ لم أجد اسم يحتوي على: {q}"

# ============ أوامر البوت ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بك! أرسل رقم الجلوس أو الاسم للبحث.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text.isdigit():
        reply = search_by_number(text)
    else:
        reply = search_by_name(text)
    await update.message.reply_text(reply)

# ============ إعداد Telegram + Flask ============
telegram_app = Application.builder().token(TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

app = Flask(__name__)

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    telegram_app.update_queue.put_nowait(update)
    return "ok"

@app.route("/")
def index():
    return "🤖 البوت شغال"

if __name__ == "__main__":
    import asyncio
    async def set_webhook():
        await telegram_app.bot.set_webhook(WEBHOOK_URL)
        log.info(f"✅ Webhook set: {WEBHOOK_URL}")
    asyncio.run(set_webhook())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
