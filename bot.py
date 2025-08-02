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
▫️ واجهة سهلة الاستخدام

📌 **المنصات المدعومة:**
- تيك توك (بدون علامة مائية)
- يوتيوب (بجودة 1080p)
- إنستغرام (قصص/ريلز/منشورات)
- تويتر/X (فيديوهات متعددة)

⚡ **طريقة الاستخدام:**
1. أرسل رابط الفيديو
2. انتظر ثوانٍ قليلة
3. استلم الفيديو بجودة عالية
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("مشاركة البوت 📲", url="https://t.me/share/url?url=https://t.me/AllDownloadspeed_bot")]
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
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls']
                }
            },
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
            
    except yt_dlp.utils.DownloadError as e:
        if "Sign in to confirm" in str(e):
            await msg.edit_text("⚠️ يوتيوب يطلب تأكيد الهوية، جرب رابطًا آخر")
        else:
            await msg.edit_text(f"❌ خطأ في التحميل: {str(e)}")
    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ غير متوقع: {str(e)}")
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

if __name__ == '__main__':
    try:
        os.makedirs("downloads", exist_ok=True)
        app = ApplicationBuilder().token(TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
        
        print("🟢 البوت يعمل الآن...")
        app.run_polling()
        
    except Conflict:
        print("🔴 البوت يعمل بالفعل في مكان آخر!")
        sys.exit(1)
