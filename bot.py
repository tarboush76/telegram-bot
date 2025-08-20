
import logging
import pandas as pd
from telegram.ext import Updater, MessageHandler, Filters

# ---------- إعداد ملف الإكسل ----------

df = pd.read_excel("results.xlsx", header=0)  # إذا الصف الأول فعلاً عناوين
df.columns = df.columns.str.strip()
df["Number"] = df["Number"].astype(str).str.strip()

# ---------- التوكن ----------
TOKEN = "429620974:AAEXymUdVhTYSYiWJ_lMhAULtitVypoQrq8"

# ---------- لوج للتصحيح ----------
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    level=logging.INFO)

# ---------- دالة جلب النتيجة ----------
def get_result(roll_number):
    roll_number = str(roll_number).strip()
    result = df[df["Number"] == roll_number]
    if not result.empty:
        row = result.iloc[0]
        output_lines = []
        for col in df.columns:     # ← نمر على كل الأعمدة بعد التنظيف
            if col == "Number":    # ← تجاهل رقم الجلوس
                continue
            value = row[col]
            if isinstance(value, (int, float)):
                status = "✅" if value >= 50 else "❌"
                output_lines.append(f"{col}: {value} {status}")
            else:
                output_lines.append(f"{col}: {value}")
        return "\n".join(output_lines)
    else:
        return "تأكد أنك أدخلت رقم الجلوس الصحيح"

# ---------- استقبال الرسائل ----------
def handle_message(update, context):
    roll_number = update.message.text
    result_text = get_result(roll_number)
    update.message.reply_text(result_text)

# ---------- تشغيل البوت ----------
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()