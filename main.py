import os
import logging
import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# ---------------- إعداد اللوج ----------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- قراءة التوكن ----------------
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود. أضفه في Render → Environment.")

# ---------------- تحميل ملفات الإكسل ----------------
DATA = {}  # year -> DataFrame

def load_excel(year: int, filename: str):
    if os.path.exists(filename):
        try:
            df = pd.read_excel(filename)
            # توحيد اسم العمود الخاص برقم الجلوس (id أو Number)
            cols = {c.lower().strip(): c for c in df.columns}
            number_col = None
            for key in ["number", "رقم", "id", "seat", "roll", "رقم_الجلوس"]:
                if key in cols:
                    number_col = cols[key]
                    break
            if not number_col:
                # محاولة ذكية: لو في عمود اسمه قريب
                for c in df.columns:
                    if c.strip().lower() in ["number", "id", "seat", "roll", "رقم", "رقم_الجلوس"]:
                        number_col = c
                        break
            if not number_col:
                logger.warning(f"⚠️ لم يتم العثور على عمود رقم الجلوس في {filename}.")
                return None

            # تنظيف أرقام الجلوس إلى نصوص موحّدة
            df[number_col] = df[number_col].astype(str).str.strip()
            DATA[year] = (df, number_col)
            logger.info(f"✅ تم تحميل {filename} لسنة {year} (عمود الرقم: {number_col})")
        except Exception as e:
            logger.exception(f"❌ خطأ أثناء تحميل {filename}: {e}")
    else:
        logger.warning(f"ℹ️ الملف {filename} غير موجود، سيتم تجاهله.")

# حمّل الملفات المتوقعة:
load_excel(2023, "2023.xlsx")
load_excel(2024, "2024.xlsx")
load_excel(2025, "2025.xlsx")

def infer_year_from_roll(roll: str) -> int | None:
    roll = roll.strip()
    if not roll:
        return None
    first = roll[0]
    mapping = {"3": 2023, "4": 2024, "5": 2025}
    return mapping.get(first)

def format_result_row(row, number_col: str) -> str:
    """
    تنسيق جميل للرد بدون إظهار عناوين الأعمدة كصف،
    فقط نعرض كل عمود (عدا رقم الجلوس) كسطر: اسم_المادة: الدرجة ✅/❌
    قاعدة النجاح الافتراضية: 50 فما فوق ✅
    """
    parts = []
    for col in row.index:
        if col == number_col:
            continue
        val = row[col]
        # لو رقم: نحكم نجاح/رسوب
        if isinstance(val, (int, float)) and pd.notnull(val):
            status = "✅" if float(val) >= 50 else "❌"
            parts.append(f"{col}: {val} {status}")
        else:
            # نص أو فراغ
            if pd.isna(val):
                parts.append(f"{col}: -")
            else:
                parts.append(f"{col}: {val}")
    return "\n".join(parts)

def search_result(roll: str, year: int) -> str:
    if year not in DATA:
        return "❌ العام غير مدعوم أو لم يتم رفع ملفه."
    df, number_col = DATA[year]
    if df is None or number_col is None or df.empty:
        return "⚠️ قاعدة البيانات غير محمّلة بشكل صحيح."
    q = str(roll).strip()
    result = df[df[number_col] == q]
    if result.empty:
        return "❌ لا توجد نتيجة لهذا الرقم."
    row = result.iloc[0]
    return format_result_row(row, number_col)

# ---------------- الأوامر والرسائل ----------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 أهلاً بك!\n\n"
        "أرسل رقم الجلوس فقط وسيتم تحديد العام تلقائياً:\n"
        "مثال: 456890\n\n"
        "أو أرسل الرقم مع العام:\n"
        "مثال: 456890 2024\n\n"
        "السنوات المدعومة: 2023، 2024، 2025."
    )
    await update.message.reply_text(msg)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("أرسل رقم الجلوس، أو رقم الجلوس متبوعاً بالسنة.")
        return

    parts = text.split()
    roll = None
    year = None

    if len(parts) == 1:
        # رقم فقط → استنتاج سنة من أول رقم
        roll = parts[0]
        year = infer_year_from_roll(roll)
        if not year:
            await update.message.reply_text(
                "⚠️ لم أتمكن من تحديد العام من الرقم.\n"
                "أرسل بالشكل: 456890 2024"
            )
            return
    elif len(parts) >= 2:
        roll = parts[0]
        try:
            year = int(parts[1])
        except:
            await update.message.reply_text("⚠️ العام غير صحيح. أرسل بالشكل: 456890 2024")
            return
    else:
        await update.message.reply_text("أرسل رقم الجلوس، أو رقم الجلوس متبوعاً بالسنة.")
        return

    reply = search_result(roll, year)
    await update.message.reply_text(reply)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("🚀 بدء تشغيل البوت (polling)")
    app.run_polling()

if __name__ == "__main__":
    main()
