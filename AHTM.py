import os
import logging
import pandas as pd
import tempfile
import arabic_reshaper
from bidi.algorithm import get_display
from telegram import Update, InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
import json
import traceback

# ===== تحميل متغيرات البيئة =====
from dotenv import load_dotenv
load_dotenv()

# ===== اللوج =====
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger("results-bot")

# ===== التوكن =====
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN غير موجود. أضِفه في Secrets")

# ===== تسجيل خط عربي =====
try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    FONT_PATH = "Amiri-Regular.ttf"
    if os.path.exists(FONT_PATH):
        pdfmetrics.registerFont(TTFont("ArabicFont", FONT_PATH))
    else:
        log.warning(f"⚠️ ملف الخط {FONT_PATH} غير موجود، قد لا يعمل إنشاء PDF بشكل صحيح.")
except ImportError as e:
    log.error(f"❌ خطأ في استيراد مكتبة reportlab: {e}")
    log.error("⚠️ لن يتمكن البوت من إنشاء ملفات PDF/HTML. تأكد من تثبيت reportlab.")


# ===== ملفات الإكسل =====
EXCEL_FILES = {
    "2021": "results_2021.xlsx",
    "2022": "results_2022.xlsx",
    "2023": "results_2023.xlsx",
    "2024": "results_2024.xlsx",
    "2025": "results_2025.xlsx"
}

dataframes = {}
def load_data():
    """تحميل جميع ملفات الإكسل إلى الذاكرة."""
    log.info("⏳ جاري تحميل ملفات الإكسل...")
    global dataframes
    dataframes.clear()
    for year, filename in EXCEL_FILES.items():
        try:
            if os.path.exists(filename):
                df = pd.read_excel(filename, engine="openpyxl")
                df = df.dropna(how="all")
                df.columns = [str(c).strip() for c in df.columns]
                dataframes[year] = df
                log.info(f"✅ تم تحميل {filename} ({len(df)} صف)")
            else:
                log.warning(f"⚠️ الملف {filename} غير موجود.")
        except Exception as e:
            log.error(f"❌ خطأ في تحميل {filename}: {e}")
    log.info("✅ انتهى تحميل البيانات.")

# تأكد من وجود البيانات قبل التشغيل
try:
    load_data()
    if not dataframes:
        log.critical("❌ لم يتم العثور على أي ملف نتائج. البوت سيعمل بدون بيانات.")
except Exception as e:
    log.critical(f"❌ فشل تحميل البيانات عند البدء: {e}")
    dataframes = {}


# ===== دوال الإحصائيات =====
STATS_FILE = "stats.json"

def load_stats():
    """تحميل الإحصائيات من ملف JSON"""
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                stats = json.load(f)
                return set(stats.get('users_set', [])), stats.get('total_queries', 0)
        except (json.JSONDecodeError, FileNotFoundError):
            log.error(f"❌ خطأ في قراءة ملف JSON أو الملف غير موجود. ستبدأ الإحصائيات من الصفر.")
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

# ===== دوال عامة =====
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

    # قاموس لترجمة أسماء الإكسل إلى الأسماء الكاملة في التقرير
    arabic_display_names = {
        "القران": "القران الكريم",
        "الاسلامية": "التربية الاسلامية",
        "العربي": "اللغة العربية",
        "الانجليزي": "اللغة الانجليزية",
        "الرياضيات": "الرياضيات",
        "العلوم": "العلوم",
        "الاحتماعيات": "الاجتماعيات"
    }
 
    filepath = os.path.join(tempfile.gettempdir(), filename)

    #  تم التعديل هنا ليكون البحث عن اسم المدرسة والمديرية مرناً
    student_name = 'N/A'
    for col in ['الاسم', 'Name']:
        if col in row and pd.notna(row[col]):
            student_name = row[col]
            break

    seat_number = 'N/A'
    for col in ['Number', 'number']:
        if col in row and pd.notna(row[col]):
            seat_number = row[col]
            break

    school_name = 'N/A'
    for col in ['المدرسة', 'المدرسه', 'اسم المدرسة', 'School']:
        if col in row and pd.notna(row[col]):
            school_name = str(row[col]).strip()
            break

    directorate_name = 'N/A'
    for col in ['المديرية', 'المديريه', 'Directorate']:
        if col in row and pd.notna(row[col]):
            directorate_name = str(row[col]).strip()
            break

    final_result = row.get('النتيجة', 'N/A')
    total_score = row.get('المجموع', 0)
    average_score = row.get('المعدل', 'N/A')
    notes = row.get('ملاحظات', '')
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
                # استخدام القاموس الجديد للحصول على الاسم الكامل
                arabic_display_name = arabic_display_names.get(col_name, col_name)
                grade_value = int(val) if isinstance(val, (int, float)) else str(val)
                # تم التعديل هنا: استخدام arabic_display_name وتغيير حجم الخط إلى 11
                grades_rows_html += f'''
<tr class="odd">
    <td align="center"><b><span style="font-size: 13px;">{arabic_display_name}</span></b></td> <td align="center">100</td>
    <td class="small-col" align="center">50</td> <td align="center" class=" nowrap"><h4><b>{grade_value}</b></h4></td>
    <td align="center"><b><span style="font-size: 12px;">{english_name}</span></b></td>
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
            /* تم تصحيح المشكلة هنا */
            .info-title h2 b {{ font-size: inherit; }}
            /* تنسيق حجم الخط للعناوين الرئيسية */
            .info-header-container h2, .school-line h2, .name-line h2, .birth-info h2 {{
                font-size: 1.5em !important;
                font-weight: bold !important;
            }}
            /* تصغير عرض أعمدة الدرجات */
            .small-col {{ width: 2cm !important; }}
            @media print {{ @page {{ size: A4; margin: 0; }} body {{ margin: 0; padding: 0; }} .container-non-responsive {{ max-width: 100%; width: 100%; margin: 0; padding: 10px; border: none; box-shadow: none; font-size: 11pt; }} .success2 th, .success2 td {{ font-size: 10pt; }} h4, h2 {{ font-size: 12pt !important; }} .title-line {{ font-size: 14pt !important; }} .name-line {{ font-size: 12pt !important; }} }}
        </style>
    </head>
    <body dir="rtl" lang="ar">
        <div class="container-non-responsive">
            <div id="result"> <div id="ra">
                <div class="info-header-container">
                    <div class="title-line"><h2><b>نتيجة الصف التاسع للعام {year}/{int(year)-1}</b></h2></div>
                  <<div style="text-align: right;">
    <h2 style="display: inline-block; border: 1px solid #000; padding: 10px; border-radius: 10px; margin-bottom: 0;"><b>رقم الجلوس : {seat_number}</b></h2>
</div>
     <div class="name-line" style="text-align: right;"><h2><b>اسم الطالب : {student_name}</b></h2></div>
<div class="school-line">
    <div style="text-align: right;"><h2 style="margin-top: 0;"><b>المدرسة : {school_name}</b></h2></div>
    <div style="text-align: left;"><h2 style="margin-top: 0;"><b>المديرية : {directorate_name}</b></h2></div>
</div>
                          <div class="birth-info">
                    <div style="text-align: right;"><h2><b>محل الميلاد : {birth_place}</b></h2></div>
                    <div style="text-align: left;"><h2><b>تاريخ الميلاد : {birth_date}</b></h2></div>
                </div>
                <div class="table-responsive"> <table class="success2">
                <thead>
                    <tr style="border-top: 2px solid;"><td style="border:none;" colspan="5"><h2 style="font-size: 18px;"><b>درجات المواد / TRANSCRIPT</b></h2></td></tr>
                    <tr> <th><center>المواد الدراسية</center></th> <th class="small-col"><center>النهاية الكبرى</center></th> <th class="small-col"><center>النهاية الصغرى</center></th> <th><center>الدرجة المستحقة</center></th> <th class=""><center>SUBJECTS</center></th> </tr>
                </thead>
                <tbody> {grades_rows_html}
                    <tr style="font-weight:bold;">
                        <td align="center">المجموع</td> <td align="center"><h4>{max_total if max_total > 0 else 'N/A'}</h4></td>
                        <td align="center" class="small-col"><h4>{max_total/2 if max_total > 0 else 'N/A'}</h4></td> <td align="center"><h4>{total_score}</h4></td>
                        <td align="center">Total</td>
                    </tr>
                </tbody>
                </table> </div> <br />
            <div class="na" style="display: flex; justify-content: flex-start; align-items: center; gap: 3cm;">
    <div style="text-align: right;">
       <span style="font-weight:bold;"> النتيجة النهائية : <span style="font-weight:bold;">{final_result}</span></span>
    </div>
    <div style="text-align: left;">
       <span>المعدل : {average_str} %</span>
        </div>
           </div>
      <div class="na" style="text-align: center;">
      <span> الملاحظات : <span style="font-weight:bold; color:red;">{notes}</span></span>
             </div>
                <br/><br/> <center><span style="color:red;"><b>*ملاحظة : </b></span> لا يعتبر هذا البيان وثيقة رسمية.</center>
            </div> <br /><br /> <center><a href="javascript:window.print()" class="btn btn-success btn-lg">طباعة النتيجة</a></center> </div>
            <div id="footer"> <p>جميع الحقوق محفوظة &copy; لـ مكتب التربية والتعليم - اليمن - تعز</p> <p>برمجة وتصميم: خالد طربوش</p> </div>
        </div>
    </body>
    </html>"""

    with open(filepath, "w", encoding="utf-8") as f: f.write(html_template)
    return filepath


# ===== أوامر =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log.info("✅ تم استقبال أمر /start")
    global users_set, total_queries
    users_set.add(update.effective_user.id)
    save_stats(users_set, total_queries)
    msg = ("👋 أهلاً بك في بوت نتائج الصف التاسع - محافظة تعز\n\n" "🔍 أرسل رقم الجلوس أو أرسل الاسم للبحث\n\n" "🔧 تصميم وتطوير: خالد طربوش")
    await update.message.reply_text(msg)

async def howm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log.info("✅ تم استقبال أمر /howm")
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
    except Exception as e:
        log.error(f"❌ فشل في إنشاء HTML: {e}")
        print(f"❌ خطأ في إنشاء أو إرسال ملف HTML: {e}")
        traceback.print_exc()

# ===== معالجة الرسائل العادية (بحث) =====
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log.info("⏳ جاري معالجة رسالة نصية...")
    global total_queries, users_set
    users_set.add(update.effective_user.id)
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("❌ أرسل رقم الجلوس أو الاسم.")
        return

    # تحديث الإحصائيات
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
        log.info(f"✅ تم إرسال نتيجة الرقم: {text}")
        return

    # بداية تعديل جزء البحث بالاسم
    user_data = context.user_data
    # Check if the user is searching for the same name again
    if 'last_query' in user_data and user_data['last_query'] == text:
        all_results = user_data['all_results']
        results_sent_count = user_data['results_sent_count']

        if results_sent_count >= len(all_results):
            await update.message.reply_text("❌ لم يتم العثور على نتائج أخرى لهذا الاسم.")
            return

        # Determine the start and end index for the next batch
        start_index = results_sent_count
        end_index = min(results_sent_count + 3, len(all_results))

        # Send the next batch of results
        for row, year in all_results[start_index:end_index]:
            await process_and_send_results(row, year, update)
            log.info(f"✅ تم إرسال نتيجة للاسم: {text} - جزء إضافي.")

        # Update the counter
        user_data['results_sent_count'] = end_index
        return

    # If it's a new name search, reset the state
    user_data['last_query'] = text
    user_data['all_results'] = []
    user_data['results_sent_count'] = 0

    all_results = []
    # Search for the name across all years and store all results
    for year, df in dataframes.items():
        name_cols = [c for c in df.columns if str(c).strip() == "الاسم"]
        if not name_cols:
            continue
        name_col = name_cols[0]
        mask = df[name_col].astype(str).str.contains(text, case=False, na=False)
        result = df[mask]
        if not result.empty:
            for _, row in result.iterrows():
                all_results.append((row, year))

    if not all_results:
        await update.message.reply_text("❌ لم يتم العثور على أي نتائج تطابق هذا الاسم.")
        log.info(f"❌ لم يتم العثور على نتائج للاسم: {text}")
        # Clear the state to allow for a new search
        user_data.pop('last_query', None)
        user_data.pop('all_results', None)
        user_data.pop('results_sent_count', None)
        return

    # Store all found results and initialize the counter
    user_data['all_results'] = all_results

    # Get the first 3 results, prioritizing different years
    results_to_send = []
    years_sent = set()
    for row, year in all_results:
        if len(results_to_send) >= 3:
            break
        if year not in years_sent:
            results_to_send.append((row, year))
            years_sent.add(year)

    # If we couldn't get 3 from different years, just take the first 3
    if len(results_to_send) < 3 and len(all_results) > len(results_to_send):
        remaining_count = 3 - len(results_to_send)
        for row, year in all_results:
            if remaining_count == 0:
                break
            if (row, year) not in results_to_send:
                results_to_send.append((row, year))
                remaining_count -= 1

    await update.message.reply_text(f"🔍 تم العثور على {len(all_results)} نتيجة. سيتم إرسال أفضل {len(results_to_send)} نتيجة:")

    for row, year in results_to_send:
        await process_and_send_results(row, year, update)
        log.info(f"✅ تم إرسال نتيجة للاسم: {text} - الدفعة الأولى.")

    # Update the counter after sending the first batch
    user_data['results_sent_count'] = len(results_to_send)

# ===== دوال تحديث البيانات (للمسؤول) =====
GET_PASSWORD, GET_YEAR = range(2)
UPDATE_PASSWORD = "1122334455"

async def handle_excel_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الخطوة 1: استلام ملف إكسل وطلب كلمة السر."""
    log.info("⏳ تم استقبال ملف إكسل. جاري طلب كلمة السر.")
    await update.message.reply_text("ماذا تريد أن تفعل؟")
    keyboard = [[InlineKeyboardButton("تحديث (update)", callback_data="update")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("اختر الإجراء:", reply_markup=reply_markup)

    context.user_data['file_id'] = update.message.document.file_id
    context.user_data['action'] = 'update'
    return GET_PASSWORD

async def handle_update_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    log.info("⏳ تم الضغط على زر التحديث. جاري طلب كلمة السر.")
    await query.edit_message_text(text="الرجاء إدخال كلمة السر للتحديث:")
    return GET_PASSWORD

async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الخطوة 2: التحقق من كلمة السر وطلب السنة."""
    password = update.message.text
    if password == UPDATE_PASSWORD:
        context.user_data['password_correct'] = True
        years_list = "، ".join(EXCEL_FILES.keys())
        log.info("✅ كلمة السر صحيحة.")
        await update.message.reply_text(f"كلمة السر صحيحة. ما هو العام المطلوب تحديث البيانات إليه؟\nالسنوات المتاحة: {years_list}")
        return GET_YEAR
    else:
        context.user_data['password_correct'] = False
        log.warning("❌ كلمة سر غير صحيحة.")
        await update.message.reply_text("❌ كلمة السر غير صحيحة. حاول مرة أخرى أو أرسل /cancel للخروج.")
        return GET_PASSWORD

async def update_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الخطوة 3: تحديث ملف الإكسل بإضافة البيانات الجديدة."""
    year_to_update = update.message.text.strip()
    if year_to_update not in EXCEL_FILES:
        await update.message.reply_text(f"❌ العام المدخل غير صحيح. السنوات المتاحة هي: {', '.join(EXCEL_FILES.keys())}. حاول مرة أخرى أو أرسل /cancel للخروج.")
        return GET_YEAR

    file_id = context.user_data.get('file_id')
    if not file_id:
        await update.message.reply_text("❌ حدث خطأ، لم يتم العثور على الملف. يرجى البدء من جديد بإرسال الملف.")
        return ConversationHandler.END

    new_file = await context.bot.get_file(file_id)
    temp_file_path = f"{tempfile.gettempdir()}/{new_file.file_path.split('/')[-1]}"
    log.info(f"⏳ جاري تنزيل الملف الجديد: {temp_file_path}")
    await new_file.download_to_drive(temp_file_path)

    try:
        new_df = pd.read_excel(temp_file_path, engine="openpyxl")
        new_df = new_df.dropna(how="all")
        new_df.columns = [str(c).strip() for c in new_df.columns]

        target_filename = EXCEL_FILES[year_to_update]

        if os.path.exists(target_filename):
            existing_df = pd.read_excel(target_filename, engine="openpyxl")
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df.drop_duplicates(subset=['Number'], keep='last', inplace=True)
            log.info(f"✅ تم دمج البيانات الجديدة مع البيانات الموجودة لملف {target_filename}.")
        else:
            combined_df = new_df
            log.info(f"✅ تم إنشاء ملف جديد لـ {target_filename}.")

        combined_df.to_excel(target_filename, index=False)
        await update.message.reply_text(f"✅ تم تحديث بيانات العام {year_to_update} بنجاح! تم إضافة {len(new_df)} سجل جديد.")
        log.info(f"✅ تم حفظ الملف الجديد {target_filename} بنجاح.")

        load_data()
        await update.message.reply_text("✅ تم إعادة تحميل البيانات في البوت لتشمل التحديثات.")

    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ أثناء معالجة الملف: {e}")
        log.error(f"❌ خطأ في معالجة الملف: {e}")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء المحادثة."""
    await update.message.reply_text('تم إلغاء العملية.')
    return ConversationHandler.END

# ===== التشغيل =====
def main():
    log.info("🚀 بدء تشغيل البوت...")
    try:
        app = Application.builder().token(TOKEN).build()

        update_handler = ConversationHandler(
            entry_points=[MessageHandler(filters.Document.ALL, handle_excel_file)],
            states={
                GET_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password)],
                GET_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_data)],
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("howm", howm))
        app.add_handler(update_handler)
        app.add_handler(CallbackQueryHandler(handle_update_button, pattern="^update$"))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

        log.info("✅ تم تهيئة المعالجات. البوت جاهز للاستماع...")
        app.run_polling()
    except Exception as e:
        log.critical(f"❌ توقف البوت بسبب خطأ غير متوقع: {e}")
        log.critical("Traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
