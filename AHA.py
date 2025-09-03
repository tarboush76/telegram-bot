import os
import logging
import pandas as pd
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

# ============ إعداد اللوج ============
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
log = logging.getLogger("results-bot")

# ============ التوكن ============
TOKEN = os.getenv("BOT_TOKEN") or "ضع_التوكن_هنا"

# ============ تحميل ملفات الإكسل ============
EXCEL_FILES = {
    "2021": "results_2021.xlsx",
    "2022": "results_2022.xlsx",
    "2023": "results_2023.xlsx",
    "2024": "results_2024.xlsx",
    "2025": "results_2025.xlsx"
}

dataframes = {}
for year, filename in EXCEL_FILES.items():
    try:
        if os.path.exists(filename):
            df = pd.read_excel(filename, engine="openpyxl")
            dataframes[year] = df
            log.info(f"✔ تم تحميل {filename} ({len(df)} صف)")
        else:
            log.warning(f"⚠ الملف {filename} غير موجود")
    except Exception as e:
        log.error(f"❌ خطأ في تحميل {filename}: {e}")

if not dataframes:
    raise RuntimeError("❌ لم يتم العثور على أي ملف نتائج")

# ============ أدوات البحث ============
def get_year_from_number(number: str) -> str:
    if not number: return None
    if number.startswith("5"): return "2025"
    if number.startswith("8"): return "2024"
    if number.startswith("3"): return "2023"
    if number.startswith("2"): return "2022"
    if number.startswith("1"): return "2021"
    return None

def format_row(row: pd.Series, df, year: str) -> str:
    text = []
    text.append(f"📅 السنة: {year}")
    if "Number" in df.columns:
        text.append(f"🔢 رقم الجلوس: {row['Number']}")
    if "الاسم" in df.columns:
        text.append(f"👤 الاسم: {row['الاسم']}")
    elif "Name" in df.columns:
        text.append(f"👤 الاسم: {row['Name']}")

    for col in df.columns:
        if col.lower() not in ["number", "الاسم", "name"]:
            val = row[col]
            if pd.isna(val):
                val = "-"
            text.append(f"{col}: {val}")
    return "\n".join(text)

# ============ توليد PDF ============
def generate_pdf(text: str) -> io.BytesIO:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica", 12)
    y = height - 50
    for line in text.split("\n"):
        c.drawString(50, y, str(line))
        y -= 20
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ============ أوامر البوت ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً! أرسل رقم الجلوس أو الاسم للبحث عن نتيجتك. وسيصلك ملف PDF بالنتيجة.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = (update.message.text or "").strip()
    if not q:
        await update.message.reply_text("❌ أرسل رقم الجلوس أو الاسم.")
        return

    results_found = []

    # بحث برقم الجلوس
    if q.isdigit():
        year = get_year_from_number(q)
        if year and year in dataframes:
            df = dataframes[year]
            if "Number" in df.columns:
                result = df[df["Number"].astype(str).str.strip() == q]
                if not result.empty:
                    row = result.iloc[0]
                    response = format_row(row, df, year)
                    pdf_buffer = generate_pdf(response)
                    await update.message.reply_document(document=InputFile(pdf_buffer, filename=f"result_{q}.pdf"))
                    return
        await update.message.reply_text(f"❌ لم أجد رقم الجلوس {q}.")
        return

    # بحث بالاسم
    for year, df in dataframes.items():
        name_col = None
        for col in ["الاسم", "Name"]:
            if col in df.columns:
                name_col = col
                break
        if name_col:
            mask = df[name_col].astype(str).str.contains(q, case=False, na=False)
            res = df[mask]
            if not res.empty:
                for _, row in res.iterrows():
                    response = format_row(row, df, year)
                    pdf_buffer = generate_pdf(response)
                    await update.message.reply_document(document=InputFile(pdf_buffer, filename=f"result_{year}.pdf"))
                return

    await update.message.reply_text(f"❌ لم أجد أي نتيجة تحتوي على '{q}'.")

# ============ تشغيل البوت ============
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    log.info("🚀 البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
