import os
import logging
import yt_dlp
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from flask import Flask
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

# Multi-language support
LANGUAGES = {
    'en': {
        'start_message': """
📥 **Advanced Download Bot** 🚀

▫️ Supports all platforms (Instagram, TikTok, Twitter, Facebook)
▫️ HD quality without distortion
▫️ Ultra-fast downloading
▫️ Send the video link and it will be downloaded
""",
        'processing': "⏳ Processing your request...",
        'success': "✅ Download complete",
        'error': "❌ Error occurred",
        'size_limit': "⚠️ File exceeds 1000MB limit",
        'share': "Share Bot 📲",
        'support': "Technical Support"
    },
    'ar': {
        'start_message': """
📥 **بوت التحميل المتقدم** 🚀

▫️ يدعم جميع المنصات (إنستجرام، تيك توك، تويتر، فيسبوك)
▫️ جودة HD بدون تشويه
▫️ سرعة فائقة في التحميل
▫️ أرسل رابط المقطع وسيتم تحميله
""",
        'processing': "⏳ جاري معالجة طلبك...",
        'success': "✅ تم التحميل بنجاح",
        'error': "❌ حدث خطأ",
        'size_limit': "⚠️ الملف يتجاوز الحد المسموح (1000MB)",
        'share': "مشاركة البوت 📲",
        'support': "الدعم الفني"
    }
}

def detect_language(update: Update) -> str:
    """Detect user language based on Telegram client settings"""
    if update.effective_user.language_code and update.effective_user.language_code.startswith('ar'):
        return 'ar'
    return 'en'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = detect_language(update)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(LANGUAGES[lang]['share'], 
         url="https://t.me/share/url?url=https://t.me/YourBotUsername")],
        [InlineKeyboardButton(LANGUAGES[lang]['support'], 
         url="https://t.me/YourSupportChannel")]
    ])
    await update.message.reply_text(LANGUAGES[lang]['start_message'], reply_markup=keyboard)

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    lang = detect_language(update)
    msg = await update.message.reply_text(LANGUAGES[lang]['processing'])
    
    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="upload_video"
        )
        
        # URL normalization for mobile apps
        url = (url
              .replace("instagram.com", "ddinstagram.com")
              .replace("x.com", "fxtwitter.com")
              .replace("twitter.com", "fxtwitter.com")
              .replace("facebook.com", "fdown.net")
              .replace("tiktok.com", "tiktx.com")
              .replace("vm.tiktok.com", "tiktx.com")
              .replace("m.facebook.com", "fdown.net")
              .replace("m.instagram.com", "ddinstagram.com"))
        
        ydl_opts = {
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'format': 'best[filesize<1000M]',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
                'Referer': 'https://www.google.com/'
            },
            'force_generic_extractor': True,
            'quiet': True,
            'extractor_args': {
                'instagram': {'skip': ['auth']},
                'facebook': {'skip': ['auth']},
                'tiktok': {'skip': ['auth']}
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Check file size
            if info.get('filesize', 0) > 1000 * 1024 * 1024:  # 1000MB limit
                await msg.edit_text(LANGUAGES[lang]['size_limit'])
                return
                
            file_path = ydl.prepare_filename(info)
            
            with open(file_path, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=video_file,
                    caption=LANGUAGES[lang]['success'],
                    supports_streaming=True,
                    read_timeout=60,
                    write_timeout=60,
                    connect_timeout=60
                )
        await msg.delete()
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"Download error: {str(e)}")
        await msg.edit_text(f"{LANGUAGES[lang]['error']}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        await msg.edit_text(f"{LANGUAGES[lang]['error']}: {str(e)}")
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

async def run_bot():
    """Run the Telegram bot with proper event loop"""
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    
    # Start the bot
    await application.run_polling()

def run_flask_app():
    """Run Flask app using Waitress"""
    serve(app, host='0.0.0.0', port=8080)

def setup_bot():
    """Setup bot with new event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())

if __name__ == '__main__':
    try:
        # Create downloads directory if not exists
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        # Start bot and Flask in separate threads
        bot_thread = threading.Thread(target=setup_bot, daemon=True)
        flask_thread = threading.Thread(target=run_flask_app, daemon=True)
        
        bot_thread.start()
        flask_thread.start()
        
        logger.info("✅ Bot and Flask server started successfully")
        
        # Keep main thread alive
        while True:
            pass
            
    except Exception as e:
        logger.critical(f"❌ Failed to start bot: {str(e)}")
        raise
