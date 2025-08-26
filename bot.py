import os
import logging
import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد اللوج
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
log = logging.getLogger("results-bot")

# قراءة التوكن من Secrets
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN غير موجود. أضِفه في Secrets على Render")

# تحميل ملفات الإكسل
EXCEL_FILES = {
    "2023": "results_2023.xlsx",
    "2024": "results_2024.xlsx",
    "2025": "results_2025.xlsx"
}

dataframes = {}
for year, filename in EXCEL_FILES.items():
    try:
        if os.path.exists(filename):
            dataframes[year] = pd.read_excel(filename)
            log.info(f"✅ تم تحميل ملف {year}: {filename} ({len(dataframes[year])} صف)")
        else:
            log.warning(f"⚠️ الملف {filename} غير موجود")
    except Exception as e:
        log.error(f"❌ خطأ في تحميل ملف {filename}: {e}")

if not dataframes:
    raise RuntimeError("❌ لم يتم العثور على أي ملف نتائج")

# تحديد السنة من أول رقم
def get_year_from_number(number: str) -> str:
    if number.startswith("5"):
        return "2025"
    elif number.startswith("4"):
        return "2024"
    elif number.startswith("3"):
        return "2023"
    return None

# البحث في الأعمدة
def get_columns_for_df(df):
    number_candidates = ["id", "ID", "رقم", "رقم_الجلوس", "seat", "roll"]
    name_candidates = ["name", "Name", "الاسم", "اسم", "الطالب"]

    number_col = None
    name_col = None

    for col in df.columns:
        if any(c.lower() in col.lower() for c in number_candidates):
            number_col = col
        if any(c.lower() in col.lower() for c in name_candidates):
            name_col = col

    if not number_col:
        number_col = df.columns[0]
    if not name_col:
        name_col = df.columns[1]

    return number_col, name_col

# تنسيق النتيجة
def format_row(row, df, year: str):
    number_col, name_col = get_columns_for_df(df)
    parts = [
        f"📅 السنة: {year}",
        f"👤 الاسم: {row.get(name_col, '-')}",
        f"🔢 رقم الجلوس: {row.get(number_col, '-')}"
    ]

    for col in df.columns:
        if col not in [name_col, number_col]:
            val = row.get(col, "-")
            parts.append(f"{col}: {val}")

    return "\n".join(parts)

# أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 أهلاً بك في بوت النتائج!\n\n"
        "🔍 أرسل رقم الجلوس فقط وسيظهر لك نتيجتك:\n"
        "• يبدأ بـ 5 → نتائج 2025\n"
        "• يبدأ بـ 4 → نتائج 2024\n"
        "• يبدأ بـ 3 → نتائج 2023\n\n"
        "مثال:\n"
        "`590678` (نتيجة 2025)\n"
        "`456890` (نتيجة 2024)\n"
        "`312345` (نتيجة 2023)\n"
    )
    await update.message.reply_text(msg)

# البحث عن نتيجة
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = (update.message.text or "").strip()
    if not q.isdigit():
        await update.message.reply_text("❌ أرسل رقم جلوس صحيح.")
        return

    year = get_year_from_number(q)
    if not year or year not in dataframes:
        await update.message.reply_text("❌ رقم الجلوس لا يطابق أي عام (3,4,5)")
        return

    df = dataframes[year]
    number_col, _ = get_columns_for_df(df)
    result = df[df[number_col].astype(str).str.strip() == q]

    if result.empty:
        await update.message.reply_text(f"❌ لا توجد نتيجة لرقم {q} في عام {year}")
        return

    row = result.iloc[0]
    response = format_row(row, df, year)
    await update.message.reply_text(response)

# تشغيل البوت
def main():
    log.info("🚀 بدء تشغيل البوت...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
