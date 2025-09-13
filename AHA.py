import os
import logging
import pandas as pd
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from typing import Optional
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
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
user_ids = set()

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
            # تنظيف البيانات
            df = df.dropna(how='all')  # حذف الصفوف الفارغة
            dataframes[year] = df
            log.info(f"تم تحميل ملف {year}: {filename} ({len(df)} صف)")
        else:
            log.warning(f"الملف {filename} غير موجود")
    except Exception as e:
        log.error(f"خطأ في تحميل ملف {filename}: {e}")

if not dataframes:
    raise RuntimeError("❌ لم يتم العثور على أي ملف نتائج")

def get_year_from_number(number: str) -> Optional[str]:
    """تحديد السنة من أول رقم"""
    mapping = {"5": "2025", "8": "2024", "3": "2023", "2": "2022", "4": "2021"}
    return mapping.get(number[0]) if number else None

def find_col(df, candidates):
    """البحث عن أفضل عمود مطابق"""
    for col in df.columns:
        for c in candidates:
            if c.lower() in str(col).lower():
                return col
    return None

def get_columns_for_df(df):
    """تحديد أعمدة الرقم والاسم"""
    NUMBER_COLS = ["Number","number","رقم_الجلوس","رقم","roll","seat","id","ID","الرقم"]
    NAME_COLS = ["الاسم","اسم","name","Name","الطالب","student"]
    
    num_col = find_col(df, NUMBER_COLS)
    if not num_col and len(df.columns) > 0:
        num_col = df.columns[0]
    
    name_col = find_col(df, NAME_COLS)
    if not name_col:
        for col in df.columns[1:]:
            if df[col].dtype == "object":
                name_col = col
                break
        if not name_col and len(df.columns) > 1:
            name_col = df.columns[1]
    
    return num_col, name_col

def normalize_digits(s: str) -> str:
    """تحويل الأرقام العربية إلى إنجليزية وتنظيف الرقم"""
    if not isinstance(s, str):
        s = str(s)
    
    # تحويل الأرقام العربية للإنجليزية
    trans = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    s = s.translate(trans).strip()
    
    # إزالة المسافات والرموز غير المرغوبة
    s = ''.join(c for c in s if c.isdigit())
    
    # إزالة الأصفار الزائدة من النهاية
    if s and s != "0":
        # إزالة كل الأصفار من النهاية حتى نصل لرقم لا ينتهي بصفر
        while s.endswith('0') and len(s) > 1:
            s = s[:-1]
    
    return s

# تحضير البيانات
for year, df in dataframes.items():
    num_col, name_col = get_columns_for_df(df)
    if num_col:
        # تنظيف عمود الأرقام بشكل أفضل
        df[num_col] = df[num_col].astype(str).str.strip()
        # إزالة المسافات والفواصل والنقاط
        df[num_col] = df[num_col].str.replace(r'[\s\.,]', '', regex=True)
        # إزالة أي أحرف غير رقمية
        df[num_col] = df[num_col].str.replace(r'[^\d]', '', regex=True)
        # تحويل الأرقام العربية للإنجليزية وحذف الأصفار الزائدة
        df[num_col] = df[num_col].apply(normalize_digits)
        # التأكد من عدم وجود قيم فارغة
        df[num_col] = df[num_col].replace('', '0')
    if name_col:
        # تنظيف عمود الأسماء
        df[name_col] = df[name_col].astype(str).str.strip()
    dataframes[year] = df

def format_row(row: pd.Series, df, year: str) -> str:
    """تنسيق عرض النتيجة"""
    num_col, name_col = get_columns_for_df(df)
    
    parts = [
        f"📅 السنة: {year}",
        f"👤 المدرسة: {row.get(name_col, '-') if name_col else '-'}",
        f"🔢 رقم الجلوس: {row.get(num_col, '-') if num_col else '-'}"
    ]
    
    # عرض باقي المواد/الدرجات
    for col in df.columns:
        if col not in [name_col, num_col]:
            val = row.get(col, "-")
            if pd.isna(val):
                val = "-"
            elif isinstance(val, (int, float)) and not pd.isna(val):
                status = "✅" if val >= 50 else "❌"
                parts.append(f"📚 {col}: {val} {status}")
            else:
                parts.append(f"📚 {col}: {val}")
    
    return "\n".join(parts)


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

#============ الأوامر ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البداية"""
    user_ids.add(update.effective_user.id)
    total = sum(len(df) for df in dataframes.values())
    files_info = [f"• {y}: {len(df):,} نتيجة" for y, df in dataframes.items()]
    
    msg = (
        "🎓 أهلاً بك في بوت نتائج الصف التاسع - محافظة تعز\n\n"
      "📊 البيانات المتاحة:\n" + "\n".join(files_info) +
      f"\n📈 إجمالي النتائج: {total:,}\n\n"
        "🔍 كيفية البحث:\n"
        "• الأرقام التي تبدأ بـ 5 → نتائج 2025\n"
        "• الأرقام التي تبدأ بـ 8 → نتائج 2024\n"
        "• الأرقام التي تبدأ بـ 3 → نتائج 2023\n"
        "• الأرقام التي تبدأ بـ 2 → نتائج 2022\n"
        "• الأرقام التي تبدأ بـ 4 → نتائج 2021\n"
        "• أو أرسل الاسم للبحث في جميع السنوات\n\n"
       "💡 مثال: 512345 (للبحث برقم الجلوس)\n"
      "💡 مثال: احمد محمد (للبحث بالاسم)\n\n"
        "🔧 تصميم وتطوير: خالد طربوش"
    )
    await update.message.reply_text(msg)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات البوت"""
    await update.message.reply_text(f"👥 عدد المستخدمين: {len(user_ids):,}")

async def debug_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معلومات تشخيصية عن البيانات"""
    if not context.args:
        await update.message.reply_text("استخدم: /debug 2025")
        return
    
    year = context.args[0]
    if year not in dataframes:
        await update.message.reply_text(f"❌ السنة {year} غير متاحة")
        return
    
    df = dataframes[year]
    num_col, name_col = get_columns_for_df(df)
    
    sample_numbers = df[num_col].head(10).tolist() if num_col else []
    
    info = [
        f"📊 معلومات ملف {year}:",
        f"📁 عدد الصفوف: {len(df)}",
        f"📋 عدد الأعمدة: {len(df.columns)}",
        f"🔢 عمود الأرقام: {num_col}",
        f"👤 عمود الأسماء: {name_col}",
        f"📝 عينة من الأرقام:\n{sample_numbers}"
    ]
    
    await update.message.reply_text("\n".join(info))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة النصوص"""
    try:
        user_ids.add(update.effective_user.id)
        text = (update.message.text or "").strip()
        
        if not text:
            await update.message.reply_text("⚠️ أرسل رقم الجلوس أو الاسم للبحث.")
            return

        # تنظيف النص
        text = normalize_digits(text)
        
        # البحث برقم الجلوس
        if text.isdigit():
            year = get_year_from_number(text)
            if not year or year not in dataframes:
                await update.message.reply_text(f"❌ رقم الجلوس {text} غير صحيح أو غير مدعوم")
                return
            
            df = dataframes[year]
            num_col, _ = get_columns_for_df(df)
            
            if not num_col:
                await update.message.reply_text("❌ خطأ في بيانات الملف")
                return
            
            # محاولة البحث بطرق مختلفة
            df_search = df.copy()
            df_search[num_col] = df_search[num_col].astype(str).str.strip()
            
            # البحث الأساسي
            result = df_search[df_search[num_col] == text]
            
            # إذا لم نجد نتيجة، نجرب البحث الجزئي
            if result.empty:
                result = df_search[df_search[num_col].str.contains(text, na=False)]
            
            # إذا لم نجد نتيجة، نجرب البحث بالرقم كعدد صحيح
            if result.empty:
                try:
                    numeric_mask = pd.to_numeric(df_search[num_col], errors='coerce') == int(text)
                    result = df[numeric_mask]
                except:
                    pass
            
            if result.empty:
                # طباعة معلومات تشخيصية
                log.info(f"فشل البحث عن {text} في {year}. أول 5 أرقام في الملف: {df_search[num_col].head().tolist()}")
                await update.message.reply_text(f"❌ لم أجد نتيجة للرقم {text} في عام {year}")
                return
            
            row = result.iloc[0]
            await update.message.reply_text(format_row(row, df, year))
            
        # البحث بالاسم
        else:
            all_results = []
            search_term = text.lower()
            
            for year, df in dataframes.items():
                _, name_col = get_columns_for_df(df)
                if name_col:
                    mask = df[name_col].astype(str).str.lower().str.contains(search_term, na=False)
                    matches = df[mask]
                    for _, row in matches.iterrows():
                        all_results.append((row, df, year))
            
            if not all_results:
                await update.message.reply_text(f"❌ لم أجد أي نتيجة تحتوي على: {text}")
                return
            
            # عرض أول 5 نتائج
            for i, (row, df, year) in enumerate(all_results[:5]):
                await update.message.reply_text(format_row(row, df, year))
            
            if len(all_results) > 5:
                await update.message.reply_text(f"📌 تم العثور على {len(all_results)} نتيجة، عُرضت أول 5 نتائج فقط.")

    except Exception as e:
        log.error(f"خطأ في معالجة النص: {e}")
        await update.message.reply_text("⚠️ حدث خطأ أثناء البحث. حاول مرة أخرى.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج الأخطاء"""
    log.error(f"خطأ أثناء معالجة التحديث: {context.error}")

def main():
    """الدالة الرئيسية"""
    log.info("🚀 بدء تشغيل البوت...")
    
    try:
        # إنشاء التطبيق
        app = Application.builder().token(TOKEN).build()
        
        # إضافة المعالجات
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("stats", stats))
        app.add_handler(CommandHandler("debug", debug_data))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        app.add_error_handler(error_handler)
        
        log.info("✅ البوت جاهز للعمل...")
        
   # ============ تشغيل البوت ============
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            poll_interval=1.0,
            timeout=10
        )
        
    except Exception as e:
        log.error(f"❌ خطأ في تشغيل البوت: {e}")
        raise

if __name__ == "__main__":
    main()

