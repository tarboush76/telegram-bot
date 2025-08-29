
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
    raise RuntimeError("❌ BOT_TOKEN غير موجود. أضِفه في Secrets")

# ============ تتبع المستخدمين ============
user_ids = set()  # مجموعة لحفظ معرفات المستخدمين الفريدة

# ============ تحميل ملفات الإكسل ============
EXCEL_FILES = {
    "2021": "results_2021.xlsx",
    "2022": "results_2022.xlsx",
    "2023": "results_2023.xlsx",
    "2024": "results_2024.xlsx", 
    "2025": "results_2025.xlsx"
}

# التحقق من وجود الملفات وتحميلها
dataframes = {}
for year, filename in EXCEL_FILES.items():
    try:
        if os.path.exists(filename):
            dataframes[year] = pd.read_excel(filename)
            log.info(f"تم تحميل ملف {year}: {filename} ({len(dataframes[year])} صف)")
        else:
            log.warning(f"الملف {filename} غير موجود")
    except Exception as e:
        log.error(f"خطأ في تحميل ملف {filename}: {e}")

if not dataframes:
    raise RuntimeError("❌ لم يتم العثور على أي ملف نتائج")

log.info(f"تم تحميل {len(dataframes)} ملف نتائج")

def get_year_from_number(number: str) -> str:
    """تحديد السنة من أول رقم في رقم الجلوس"""
    first_digit = number[0] if number else ""
    if first_digit == "5":
        return "2025"
    elif first_digit == "8":
        return "2024"
    elif first_digit == "3":
        return "2023"
    elif first_digit == "2":
        return "2022"
    elif first_digit == "4":
        return "2021"
    else:
        return None

def find_col(df, candidates):
    """البحث عن عمود من قائمة مرشحين"""
    for col in df.columns:
        for candidate in candidates:
            if candidate.lower() in col.lower():
                return col
    return None

def get_columns_for_df(df):
    """الحصول على أعمدة الرقم والاسم لملف معين"""
    NUMBER_COL_CANDIDATES = ["Number", "number", "رقم_الجلوس", "رقم", "roll", "seat", "id", "ID"]
    NAME_COL_CANDIDATES   = ["الاسم", "اسم", "name", "Name", "الطالب"]
    
    number_col = find_col(df, NUMBER_COL_CANDIDATES)
    name_col = find_col(df, NAME_COL_CANDIDATES)
    
    if not number_col:
        number_col = df.columns[0]
    
    if not name_col:
        for col in df.columns[1:]:
            if df[col].dtype == 'object':
                name_col = col
                break
        if not name_col:
            name_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
    
    return number_col, name_col

# تنظيف أرقام الجلوس في جميع الملفات
for year, df in dataframes.items():
    number_col, _ = get_columns_for_df(df)
    df[number_col] = df[number_col].astype(str).str.strip()
    dataframes[year] = df

def normalize_digits(s: str) -> str:
    """تحويل الأرقام العربية/الهندية إلى 0-9 الإنجليزية"""
    if not isinstance(s, str):
        return s
    trans = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    return s.translate(trans).strip()

def format_row(row: pd.Series, df, year: str) -> str:
    """تنسيق صف النتيجة مع معلومات السنة"""
    number_col, name_col = get_columns_for_df(df)
    
    parts = []
    parts.append(f"📅 السنة: {year}")
    parts.append(f"👤 الاسم: {row.get(name_col, '-')}")
    parts.append(f"🔢 رقم الجلوس: {row.get(number_col, '-')}")
    
    # عرض باقي الأعمدة (ماعدا الاسم والرقم)
    for col in df.columns:
        if col not in [name_col, number_col]:
            val = row.get(col, "-")
            if pd.isna(val):
                val = "-"
            # علامة نجاح/رسوب للمواد الرقمية
            if isinstance(val, (int, float)) and not pd.isna(val):
                if val >= 50:
                    status = "✅"
                else:
                    status = "❌"
                parts.append(f"{col}: {val} {status}")
            else:
                parts.append(f"{col}: {val}")
    
    return "\n".join(parts)

# ============ الأوامر والرسائل ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # إضافة المستخدم إلى قاعدة البيانات
    user_id = update.effective_user.id
    user_ids.add(user_id)
    
    files_info = []
    total_count = 0
    for year, df in dataframes.items():
        files_info.append(f"• {year}: {len(df)} نتيجة")
        total_count += len(df)
    
    msg = (
        "👋 أهلاً بك في بوت النتائج!\n\n"
        "📊 اتصميم خالد طربوش:\n" + "\n".join(files_info) + f"\n"
        f"📈 : {total_count}\n\n"
        "🔍 كيفية البحث:\n"
        "• الأرقام التي تبدأ بـ 5 → نتائج 2025\n"
        "• الأرقام التي تبدأ بـ 8 → نتائج 2024\n"
        "• الأرقام التي تبدأ بـ 3 → نتائج 2023\n"
        "• الأرقام التي تبدأ بـ 2 → نتائج 2022\n"
        "• الأرقام التي تبدأ بـ 4 → نتائج 2021\n"
        "• أو أرسل الاسم للبحث في جميع الملفات\n\n"
        "مثال:\n"
        "512345 (ستظهر نتيجة الطالب للعام 2025)\n"
        " ( وهكذا)"
    )
    await update.message.reply_text(msg)

async def howm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض عدد المستخدمين الذين دخلوا البوت"""
    total_users = len(user_ids)
    msg = f"👥 عدد المستخدمين الذين دخلوا البوت: {total_users}"
    await update.message.reply_text(msg)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # إضافة المستخدم إلى قاعدة البيانات
        user_id = update.effective_user.id
        user_ids.add(user_id)
        
        text = (update.message.text or "").strip()
        if not text:
            await update.message.reply_text("أرسل رقم الجلوس أو الاسم.")
            return

        log.info(f"البحث عن: {text}")
        q = normalize_digits(text)

        # لو كله أرقام → بحث دقيق برقم الجلوس
        if q.isdigit():
            year = get_year_from_number(q)
            if not year or year not in dataframes:
                await update.message.reply_text(f"❌ رقم الجلوس {q}  رقم الجلوس غير صحيح")
                return
            
            df = dataframes[year]
            number_col, _ = get_columns_for_df(df)
            
            result = df[df[number_col].astype(str).str.strip() == q]
            if result.empty:
                await update.message.reply_text(f"❌ لم أجد رقم الجلوس: {q} في ملف {year}")
                return
            
            row = result.iloc[0]
            response = format_row(row, df, year)
            await update.message.reply_text(response)
            log.info(f"تم العثور على النتيجة للرقم: {q} في ملف {year}")
            return

        # غير ذلك → بحث جزئي بالاسم في جميع الملفات
        all_results = []
        for year, df in dataframes.items():
            try:
                _, name_col = get_columns_for_df(df)
                mask = df[name_col].astype(str).str.contains(q, case=False, na=False)
                result = df[mask]
                
                if not result.empty:
                    for _, row in result.iterrows():
                        all_results.append((row, df, year))
                        
            except Exception as e:
                log.error(f"خطأ في البحث في ملف {year}: {e}")
                continue

        if not all_results:
            await update.message.reply_text(f"❌ لم أجد اسماً يحتوي على: {q}")
            return

        # لو النتائج كثيرة، نرسل أول 3 فقط
        MAX_ROWS = 3
        count = len(all_results)
        if count > MAX_ROWS:
            await update.message.reply_text(f"🔎 وُجد {count} نتيجة، سأعرض أول {MAX_ROWS}:")
            all_results = all_results[:MAX_ROWS]

        for row, df, year in all_results:
            response = format_row(row, df, year)
            await update.message.reply_text(response)
        
        log.info(f"تم العثور على {len(all_results)} نتائج للاسم: {q}")

    except Exception as e:
        log.error(f"خطأ في معالجة الرسالة: {e}")
        await update.message.reply_text("⚠️ حدث خطأ أثناء البحث. حاول مرة أخرى.")

def main():
    try:
        log.info("🚀 بدء تشغيل البوت...")
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("howm", howm))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

        log.info("✅ البوت جاهز وسيبدأ بوضع Polling")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        log.error(f"خطأ في تشغيل البوت: {e}")
        raise

if __name__ == "__main__":
    main()

