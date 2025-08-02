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

# BIO احترافي للبوت
BOT_DESCRIPTION = """
📥 **بوت التحميل المتقدم** 🚀

▫️ يحمل فيديوهات من كل المنصات
▫️ يدعم: تيك توك، يوتيوب، إنستغرام، تويتر
▫️ جودة عالية بدون علامة مائية
▫️ سرعة تحميل فائقة

⚡ فقط أرسل الرابط وسأحضر المحتوى لك!
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("مشاركة البوت 📲", url="https://t.me/share/url?url=https://t.me/AllDownloadspeed_bot")]
    ])
    
    start_message = f"""
    🎬 **مرحباً بك في بوت التحميل!**\n
    {BOT_DESCRIPTION}
    """
    
    await update.message.reply_text(
        start_message,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    msg = await update.message.reply_text("⏳ جاري معالجة طلبك...")
    
    try:
        # إضافة شعار أثناء التحميل
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="upload_video"
        )
        
        ydl_opts = {
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [lambda d: print(d['status'])]
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            if os.path.getsize(file_path) > 50 * 1024 * 1024:
                await msg.edit_text("⚠️ الحد الأقصى لحجم الفيديو: 50MB")
                os.remove(file_path)
                return
                
            await msg.edit_text("📤 جاري رفع الفيديو...")
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=open(file_path, 'rb'),
                caption=f"✅ تم التحميل بنجاح\n{info.get('title', '')}"
            )
            
    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ: {str(e)}")
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
        
    except Conflict as e:
        print(f"🔴 خطأ: {e} (البوت يعمل بالفعل في مكان آخر!)")
        sys.exit(1)
    except Exception as e:
        print(f"🔴 خطأ غير متوقع: {e}")
        sys.exit(1)
