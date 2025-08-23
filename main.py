import os
import logging
import pandas as pd
from typing import Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ============ إعداد اللوج ============
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
log = logging.getLogger("results-bot")

# ============ قراءة التوكن ============
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN غير موجود. أضِفه في Render → Environment Variables")

# ============ تحميل ملف الإكسل ============
EXCEL_FILE = "results.xlsx"
if not os.path.exists(EXCEL_FILE):
    raise FileNotFoundError(f"❌ الملف {EXCEL_FILE} غير موجود في نفس مجلد main.py")

df = pd.read_excel(EXCEL_FILE)

# توحيد عمود رقم الجلوس والاسم (حسب ملفك)
# المتوقّع: Number للرقم، و 'الاسم' للاسم
# لو تغيّرت أسماء الأعمدة لاحقًا، عدّل القيم هنا:
NUMBER_COL_CANDIDATES = ["Number", "number", "رقم_الجلوس", "رقم", "roll", "seat", "id"]
NAME_COL_CANDIDATES   = ["الاسم", "اسم", "name"]

def find_col(candidates):
    lower_map = {c.lower(): c for c in df.columns}
    for want in candidates:
        if want.lower() in lower_map:
            return lower_map[want.lower()]
    return None

NUMBER_COL = find_col(NUMBER_COL_CANDIDATES)
NAME_COL   = find_col(NAME_COL_CANDIDATES)

if not NUMBER_COL:
    raise ValueError("❌ لم أعثر على عمود رقم الجلوس داخل النتائج. سمّه مثلاً Number أو رقم_الجلوس")
if not NAME_COL:
    raise ValueError("❌ لم أعثر على عمود الاسم داخل النتائج. سمّه مثلاً 'الاسم'")

# تنظيف الرقم كسلسلة
df[NUMBER_COL] = df[NUMBER_COL].astype(str).str.strip()

# الأعمدة التي سنعرضها (إن وُجدت). عدّل أو زِد بحرّية
DISPLAY_COLS = [
    "المديرية", "اسم المدرسة", "القران", "الاسلاميه", "العربي",
    "الاجتماعيات", "الرياضيات", "العلوم", "الانجليزي",
    "المجموع", "المعدل", "النتيجة"
]

def normalize_digits(s: str) -> str:
    """تحويل الأرقام العربية/الهندية إلى 0-9 الإنجليزية"""
    if not isinstance(s, str):
        return s
    trans = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    return s.translate(trans).strip()

def format_row(row: pd.Series) -> str:
    parts = []
    # الاسم + الرقم
    parts.append(f"👤 الاسم: {row.get(NAME_COL, '-')}")
    parts.append(f"🔢 رقم الجلوس: {row.get(NUMBER_COL, '-')}")
    # باقي الأعمدة إن وُجدت:
    for col in DISPLAY_COLS:
        if col in df.columns:
            val = row.get(col, "-")
            if pd.isna(val):
                val = "-"
            # علامة نجاح/رسوب للمواد الرقمية
            if isinstance(val, (int, float)):
                status = "✅" if float(val) >= 50 else "❌"
                parts.append(f"{col}: {val} {status}")
            else:
                parts.append(f"{col}: {val}")
    return "\n".join(parts)

# ============ الأوامر والرسائل ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 أهلاً بك!\n"
        "أرسل رقم الجلوس للحصول على نتيجتك.\n"
        "أو أرسل الاسم وسيتم البحث الجزئي عنه.\n\n"
        "مثال (رقم): 456890\n"
        "مثال (اسم): خالد"
    )
    await update.message.reply_text(msg)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("أرسل رقم الجلوس أو الاسم.")
        return

    q = normalize_digits(text)

    # لو كله أرقام → بحث دقيق برقم الجلوس
    if q.isdigit():
        result = df[df[NUMBER_COL] == q]
        if result.empty:
            await update.message.reply_text("❌ لم أجد هذا رقم الجلوس.")
            return
        row = result.iloc[0]
        await update.message.reply_text(format_row(row))
        return

    # غير ذلك → بحث جزئي بالاسم (case-insensitive)
    try:
        result = df[df[NAME_COL].astype(str).str.contains(q, case=False, na=False)]
    except Exception:
        await update.message.reply_text("⚠️ تعذّر البحث في عمود الاسم. تأكّد من وجود عمود 'الاسم' في الملف.")
        return

    if result.empty:
        await update.message.reply_text("❌ لم أجد اسماً مطابقاً. جرّب كتابة جزء أكبر من الاسم.")
        return

    # لو النتائج كثيرة، نرسل أول 3 فقط (يمكن تعديلها)
    MAX_ROWS = 3
    count = len(result)
    if count > MAX_ROWS:
        await update.message.reply_text(f"🔎 وُجد {count} نتيجة، سأعرض أول {MAX_ROWS}:")
        result = result.head(MAX_ROWS)

    for _, row in result.iterrows():
        await update.message.reply_text(format_row(row))

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    log.info("🚀 بدء البوت بوضع Polling")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
