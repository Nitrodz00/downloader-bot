import os
import logging
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from flask import Flask, request, jsonify
from waitress import serve
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Load Environment Variables
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    logger.error("TELEGRAM_TOKEN not found in environment variables!")
    raise ValueError("TELEGRAM_TOKEN is required")

BOT_DESCRIPTION = """
📥 **بوت التحميل المتقدم** 🚀

▫️ يدعم جميع المنصات (إنستجرام، تيك توك، تويتر، فيسبوك)
▫️ جودة HD بدون تشويه
▫️ سرعة فائقة في التحميل
▫️ أرسل رابط المقطع وسيتم تحميله
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("مشاركة البوت 📲", 
         url="https://t.me/share/url?url=https://t.me/SpeedNitroDownload_bot")],
        [InlineKeyboardButton("الدعم الفني", 
         url="https://t.me/YourSupportChannel")]
    ])
    await update.message.reply_text(BOT_DESCRIPTION, reply_markup=keyboard)

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    msg = await update.message.reply_text("⏳ جاري معالجة طلبك...")
    
    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="upload_video"
        )
        
        # استبدال الروابط بواجهات عامة
        if "instagram.com" in url:
            url = url.replace("instagram.com", "ddinstagram.com")
        elif "x.com" in url or "twitter.com" in url:
            url = url.replace("x.com", "fxtwitter.com").replace("twitter.com", "fxtwitter.com")
        elif "facebook.com" in url:
            url = url.replace("facebook.com", "fdown.net")
        elif "tiktok.com" in url:
            url = url.replace("tiktok.com", "tiktx.com")
        
        ydl_opts = {
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'format': 'best[filesize<50M]',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.google.com/'
            },
            'force_generic_extractor': True,
            'quiet': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            with open(file_path, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=video_file,
                    caption=f"✅ {info.get('title', '')}",
                    supports_streaming=True
                )
        await msg.delete()
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        await msg.edit_text(f"❌ حدث خطأ: {str(e)}")
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

def setup_bot():
    """Initialize the Telegram bot with handlers"""
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    
    # Start the bot
    application.run_polling()

def run_flask_app():
    """Run Flask app using Waitress"""
    serve(app, host='0.0.0.0', port=8080)

if __name__ == '__main__':
    try:
        # Create downloads directory if not exists
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        # Start bot and Flask in separate threads
        bot_thread = threading.Thread(target=setup_bot)
        flask_thread = threading.Thread(target=run_flask_app)
        
        bot_thread.start()
        flask_thread.start()
        
        logger.info("✅ Bot and Flask server started successfully")
        
        bot_thread.join()
        flask_thread.join()
        
    except Exception as e:
        logger.critical(f"❌ Failed to start bot: {str(e)}")
        raise
