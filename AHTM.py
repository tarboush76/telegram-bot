import os
import logging
import pandas as pd
import tempfile
import arabic_reshaper
from bidi.algorithm import get_display
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import json

# ===== اللوج =====
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger("results-bot")

# ===== التوكن =====
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN غير موجود. أضِفه في Secrets")

# ===== تسجيل خط عربي =====
# تأكد من وجود ملف الخط في نفس مجلد الكود
FONT_PATH = "Amiri-Regular.ttf"
if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont("ArabicFont", FONT_PATH))
else:
    log.warning(f"⚠️ ملف الخط {FONT_PATH} غير موجود، قد لا يعمل إنشاء PDF بشكل صحيح.")


# ===== ملفات الإكسل =====
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
            df = df.dropna(how="all")
            df.columns = [str(c).strip() for c in df.columns]
            dataframes[year] = df
            log.info(f"✅ تم تحميل {filename} ({len(df)} صف)")
        else:
            log.warning(f"⚠️ الملف {filename} غير موجود")
    except Exception as e:
        log.error(f"❌ خطأ في تحميل {filename}: {e}")

if not dataframes:
    raise RuntimeError("❌ لم يتم العثور على أي ملف نتائج")

# ===== دوال الإحصائيات =====
STATS_FILE = "stats.json"

def load_stats():
    """تحميل الإحصائيات من ملف JSON"""
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                stats = json.load(f)
                return set(stats.get('users_set', [])), stats.get('total_queries', 0)
        except json.JSONDecodeError:
            log.error(f"❌ خطأ في قراءة ملف JSON. ستبدأ الإحصائيات من الصفر.")
            return set(), 0
    return set(), 0

def save_stats(users_set, total_queries):
    """حفظ الإحصائيات في ملف JSON"""
    stats = {
        'users_set': list(users_set),
        'total_queries': total_queries
    }
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f)


# ===== إحصائيات =====
users_set, total_queries = load_stats()

# ===== دوال =====
def get_year_from_number(number: str) -> str:
    """تحديد السنة من أول رقم"""
    if number.startswith("5"): return "2025"
    if number.startswith("8"): return "2024"
    if number.startswith("3"): return "2023"
    if number.startswith("2"): return "2022"
    if number.startswith("4"): return "2021"
    return None

def format_arabic(text: str) -> str:
    """معالجة النص العربي ليظهر صحيح في PDF"""
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)

def format_result_text(row: pd.Series, year: str) -> str:
    """تنسيق النتيجة كرسالة نصية"""
    text = [f"نتيجة الصف التاسع: ✅", f"📅 السنة: {year}"]
    for col, val in row.items():
        if pd.isna(val):
            val = "-"
        if str(col).lower().strip() == "number":
            col = "رقم الجلوس"
        text.append(f"{col}: {val}")
    return "\n".join(text)

def make_html_report(row: pd.Series, year: str, filename: str) -> str:
    """إنشاء ملف HTML للنتيجة بالتصميم الجديد"""
    filepath = os.path.join(tempfile.gettempdir(), filename)

    student_name = row.get('الاسم', 'N/A')
    seat_number = row.get('Number', 'N/A')
    final_result = row.get('النتيجة', 'N/A')
    total_score = row.get('المجموع', 0)
    average_score = row.get('المعدل', 'N/A')
    notes = row.get('ملاحظات', '')
    school_name = row.get('المدرسة', 'N/A')
    directorate_name = row.get('المديرية', 'N/A')
    birth_place = row.get('محل الميلاد', 'N/A')
    birth_date = row.get('تاريخ الميلاد', 'N/A')

    # تنسيق تاريخ الميلاد
    try:
        if pd.notna(birth_date):
            birth_date_dt = pd.to_datetime(birth_date)
            birth_date = birth_date_dt.strftime('%Y/%m/%d')
        else:
            birth_date = 'N/A'
    except (ValueError, TypeError):
        birth_date = str(birth_date)

    if pd.isna(notes):
        notes = ''

    grades_rows_html = ""
    subjects_count = 0
    info_cols_lower = ['number', 'المديرية', 'المدرسة', 'الاسم', 'محل الميلاد', 'تاريخ الميلاد', 'المجموع', 'المعدل', 'النتيجة', 'ملاحظات', 'العام الدراسي']
    subject_translation = {
        "القران": "Holy Quran", "الاسلامية": "Islamic Education", "العربي": "Arabic Language",
        "الانجليزي": "English Language", "الرياضيات": "Mathematics", "العلوم": "Science", "الاحتماعيات": "Social Studies",
    }

    for col, val in row.items():
        col_name = str(col).strip()
        if col_name.lower() not in [c.lower() for c in info_cols_lower] and col_name in subject_translation:
            if pd.notna(val):
                subjects_count += 1
                english_name = subject_translation.get(col_name, "")
                grade_value = int(val) if isinstance(val, (int, float)) else str(val)
                grades_rows_html += f'''
<tr class="odd">
    <td align="center"><b><span style="font-size: 12px;">{col_name}</span></b></td> <td align="center">100</td>
    <td class="hidden-xs " align="center">50</td> <td align="center" class=" nowrap"><h4><b>{grade_value}</b></h4></td>
    <td class="hidden-xs " align="center"><b><span style="font-size: 12px;">{english_name}</span></b></td>
</tr>'''

    max_total = subjects_count * 100
    average_str = f"{average_score:.2f}" if isinstance(average_score, (int, float)) else str(average_score)

    html_template = f"""
    <!DOCTYPE html>
    <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ar" lang="ar" dir="rtl">
    <head>
        <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>نتيجة الطالب - {student_name}</title>
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">
        <style>
            body {{ direction: rtl; text-align: right; background-color: #f4f4f4; }}
            .container-non-responsive {{ max-width: 1001px; margin: auto; background-color: #fff; padding: 20px; border: 1px solid #ddd; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
            #ra {{ padding: 20px; border: 1px solid #ccc; border-radius: 10px; }} .success2 {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            .success2 th, .success2 td {{ border: 1px solid #ddd; padding: 4px; text-align: center; }} .success2 thead th {{ background-color: #f2f2f2; }}
            .na {{ font-size: 20.5px; text-align: center; margin-top: 20px; }} .header-info {{ padding: 10px 20px; border: 1px solid #000; border-radius: 10px; font-size: 21px; }}
            #footer {{ text-align: center; margin-top: 20px; padding-top: 10px; border-top: 1px solid #eee; font-size: 14px; color: #777; }}
            .info-header-container {{ text-align: center; }}
            .title-line {{ font-size: 20px; font-weight: bold; margin-bottom: 10px; }}
            .box-info {{ display: flex; justify-content: space-between; align-items: center; border: 1px solid #000; padding: 10px; border-radius: 10px; margin-bottom: 10px; }}
            .box-info > div {{ flex: 1; text-align: center; }}
            .name-line, .school-line, .birth-info {{ display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 5px; }}
            .name-line {{ font-size: 18px; font-weight: bold; margin-top: 10px; }}
            .school-line > div, .birth-info > div {{ flex: 1; }}
            @media print {{ @page {{ size: A4; margin: 0; }} body {{ margin: 0; padding: 0; }} .container-non-responsive {{ max-width: 100%; width: 100%; margin: 0; padding: 10px; border: none; box-shadow: none; font-size: 11pt; }} .success2 th, .success2 td {{ font-size: 10pt; }} h4, h2 {{ font-size: 12pt !important; }} .title-line {{ font-size: 14pt !important; }} .name-line {{ font-size: 12pt !important; }} }}
        </style>
    </head>
    <body dir="rtl" lang="ar">
        <div class="container-non-responsive">
            <div id="result"> <div id="ra">
                <div class="info-header-container">
                    <div class="title-line">نتيجة الصف التاسع للعام {year}</div>
                    <div class="box-info">
                        <div style="text-align: right;">رقم الجلوس : {seat_number}</div>
                        <div style="text-align: left;">العام: {year}</div>
                    </div>
                </div>
                <div class="school-line">
                    <div style="text-align: right;">المدرسة : {school_name}</div>
                    <div style="text-align: left;">المديرية : {directorate_name}</div>
                </div>
                <div class="name-line" style="text-align: right;">اسم الطالب : {student_name}</div>
                <div class="birth-info">
                    <div style="text-align: right;">محل الميلاد : {birth_place}</div>
                    <div style="text-align: left;">تاريخ الميلاد : {birth_date}</div>
                </div>
                <div class="table-responsive"> <table class="success2">
                <thead>
                    <tr style="border-top: 2px solid;"><td style="border:none;" colspan="5"><h2 style="font-size: 18px;"><b>درجات المواد / TRANSCRIPT</b></h2></td></tr>
                    <tr> <th><center>المواد الدراسية</center></th> <th><center>النهاية الكبرى</center></th> <th class="hidden-xs"><center>النهاية الصغرى</center></th> <th><center>الدرجة المستحقة</center></th> <th class="hidden-xs"><center>SUBJECTS</center></th> </tr>
                </thead>
                <tbody> {grades_rows_html}
                    <tr style="font-weight:bold;">
                        <td align="center">المجموع</td> <td align="center"><h4>{max_total if max_total > 0 else 'N/A'}</h4></td>
                        <td class="hidden-xs " align="center"><h4>{max_total/2 if max_total > 0 else 'N/A'}</h4></td> <td align="center"><h4>{total_score}</h4></td>
                        <td class="hidden-xs " align="center">Total</td>
                    </tr>
                </tbody>
            </table> </div> <br /> <div class="na">
                <span>المعدل : {average_str} %</span><br/> <span> النتيجة النهائية : <span style="font-weight:bold;">{final_result}</span></span><br/> <span> الملاحظات : <span style="font-weight:bold;">{notes}</span></span>
            </div> <br/><br/> <center><span style="color:red;"><b>*ملاحظة : </b></span> لا يعتبر هذا البيان وثيقة رسمية.</center>
            </div> <br /><br /> <center><a href="javascript:window.print()" class="btn btn-success btn-lg">طباعة النتيجة</a></center> </div>
            <div id="footer"> <p>جميع الحقوق محفوظة &copy; لـ مكتب التربية والتعليم - اليمن - تعز</p> <p>برمجة وتصميم: خالد طربوش</p> </div>
        </div>
    </body>
    </html>"""

    with open(filepath, "w", encoding="utf-8") as f: f.write(html_template)
    return filepath


# ===== أوامر =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global users_set, total_queries
    users_set.add(update.effective_user.id)
    save_stats(users_set, total_queries)
    msg = ( "👋 أهلاً بك في بوت نتائج الصف التاسع - محافظة تعز\n\n" "🔍 أرسل رقم الجلوس أو أرسل الاسم للبحث\n\n" "🔧 تصميم وتطوير: خالد طربوش" )
    await update.message.reply_text(msg)

async def howm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = f"👥 مستخدمين: {len(users_set)}\n📊 عمليات البحث: {total_queries}"
    await update.message.reply_text(msg)

async def process_and_send_results(row: pd.Series, year: str, update: Update):
    result_text = format_result_text(row, year)
    await update.message.reply_text(result_text)

    seat_number = row.get('Number', '')

    try:
        html_file = make_html_report(row, year, f"result_{seat_number}.html")
        with open(html_file, "rb") as f:
            await update.message.reply_document(document=InputFile(f, filename=f"result_{seat_number}.html"), caption="📄 نسخة صفحة ويب (HTML)")
    except Exception as e: log.error(f"❌ فشل في إنشاء HTML: {e}")

# ===== معالجة الرسائل =====
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global total_queries, users_set
    users_set.add(update.effective_user.id)
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("❌ أرسل رقم الجلوس أو الاسم.")
        return
    total_queries += 1
    save_stats(users_set, total_queries)
    await update.message.reply_text("⏳ جارٍ البحث عن النتيجة، يرجى الانتظار...")

    if text.isdigit():
        year = get_year_from_number(text)
        if not year or year not in dataframes:
            await update.message.reply_text("❌ الرقم لا يطابق أي سنة دراسية معروفة.")
            return
        df = dataframes[year]
        number_col_options = [c for c in df.columns if str(c).lower().strip() == "number"]
        if not number_col_options:
            await update.message.reply_text(f"❌ خطأ: لا يوجد عمود 'Number' في ملفات سنة {year}.")
            return
        number_col = number_col_options[0]

        result = df[df[number_col].astype(str).str.strip() == text]
        if result.empty:
            await update.message.reply_text("❌ لم يتم العثور على نتيجة بهذا الرقم.")
            return
        row = result.iloc[0]
        await process_and_send_results(row, year, update)
        return

    all_results = []
    for year, df in dataframes.items():
        name_cols = [c for c in df.columns if str(c).strip() == "الاسم"]
        if not name_cols: continue
        name_col = name_cols[0]
        mask = df[name_col].astype(str).str.contains(text, case=False, na=False)
        result = df[mask]
        if not result.empty:
            for _, row in result.iterrows(): all_results.append((row, year))

    if not all_results:
        await update.message.reply_text("❌ لم يتم العثور على أي نتائج تطابق هذا الاسم.")
        return

    await update.message.reply_text(f"🔍 تم العثور على {len(all_results)} نتيجة، سيتم إرسال أفضل 3 نتائج مطابقة:")

    for row, year in all_results[:3]:
        await process_and_send_results(row, year, update)

# ===== التشغيل =====
def main():
    log.info("🚀 بدء تشغيل البوت...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("howm", howm))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
