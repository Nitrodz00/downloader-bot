import os
import sys
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.error import Conflict
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

BOT_DESCRIPTION = """
📥 **بوت التحميل المتقدم** 🚀

▫️ يدعم جميع المنصات الرئيسية
▫️ جودة HD بدون تشويه
▫️ سرعة فائقة في التحميل
▫️ أرسل رابط المقطع و سيتم تحميله
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("مشاركة البوت 📲", url="https://t.me/share/url?url=https://t.me/SpeedNitroDownload_bot")]
    ])
    
    await update.message.reply_text(
        BOT_DESCRIPTION,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    msg = await update.message.reply_text("⏳ جاري معالجة طلبك...")
    
    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="upload_video"
        )
        
        ydl_opts = {
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'format': 'best[filesize<50M]',
            'quiet': True,
            'no_warnings': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Accept-Language': 'en-US,en;q=0.5'
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            await msg.edit_text("📤 جاري رفع الفيديو...")
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=open(file_path, 'rb'),
                caption=f"✅ {info.get('title', '')}",
                supports_streaming=True
            )
            
    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ: {str(e)}")
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

def main():
    # إنشاء مجلد التحميلات إذا لم يكن موجوداً
    os.makedirs("downloads", exist_ok=True)
    
    try:
        app = ApplicationBuilder().token(TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
        
        print("🟢 البوت يعمل الآن...")
        app.run_polling(
            close_loop=False,
            stop_signals=None
        )
        
    except Conflict:
        print("🔴 تم اكتشاف تشغيل آخر للبوت! يرجى إيقاف جميع النسخ الأخرى.")
        sys.exit(1)
    except Exception as e:
        print(f"🔴 خطأ غير متوقع: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
