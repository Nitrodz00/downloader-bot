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
from flask import Flask, jsonify
from waitress import serve
import threading
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Security Warning: Use environment variables in production!
TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")
PORT = int(os.getenv("PORT", 10000))
MAX_FILE_SIZE = 1000 * 1024 * 1024  # 1000MB

# Multi-language support
LANGUAGES = {
    'en': {
        'start': "🎬 **Advanced Video Downloader**\n\n• Supports: Instagram, TikTok, Twitter, Facebook\n• Max size: 1000MB\n• Fast HD downloads",
        'processing': "⏳ Downloading your video...",
        'success': "✅ Download complete!",
        'error': "❌ Error:",
        'size_exceeded': "⚠️ File exceeds 1000MB limit",
        'unsupported': "🚫 Unsupported link type",
        'help': "🆘 Need help? Contact @YourSupport",
        'share': "📲 Share Bot"
    },
    'ar': {
        'start': "🎬 **بوت التحميل المتقدم**\n\n• يدعم: إنستجرام، تيك توك، تويتر، فيسبوك\n• أقصى حجم: 1000 ميجابايت\n• تحميل بجودة HD",
        'processing': "⏳ جاري تحميل الفيديو...",
        'success': "✅ اكتمل التحميل بنجاح!",
        'error': "❌ حدث خطأ:",
        'size_exceeded': "⚠️ الملف يتجاوز حد 1000 ميجابايت",
        'unsupported': "🚫 نوع الرابط غير مدعوم",
        'help': "🆘 للمساعدة تواصل @الدعم_الفني",
        'share': "📲 مشاركة البوت"
    }
}

def detect_language(update: Update) -> str:
    return 'ar' if update.effective_user and update.effective_user.language_code and 'ar' in update.effective_user.language_code else 'en'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = detect_language(update)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(LANGUAGES[lang]['share'], url="https://t.me/share/url?url=https://t.me/YourBotUsername")],
        [InlineKeyboardButton(LANGUAGES[lang]['help'], url="https://t.me/YourSupport")]
    ])
    await update.message.reply_text(LANGUAGES[lang]['start'], reply_markup=keyboard)

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = detect_language(update)
    url = update.message.text.strip()
    
    # Validate supported platforms
    if not any(x in url for x in ['instagram', 'tiktok', 'twitter', 'x.com', 'facebook']):
        await update.message.reply_text(LANGUAGES[lang]['unsupported'])
        return

    msg = await update.message.reply_text(LANGUAGES[lang]['processing'])
    
    try:
        # Mobile-friendly URL conversion
        url = (url.replace("instagram.com", "ddinstagram.com")
                .replace("x.com", "fxtwitter.com")
                .replace("twitter.com", "fxtwitter.com")
                .replace("tiktok.com", "tiktx.com")
                .replace("facebook.com", "fdown.net")
                .replace("m.facebook.com", "fdown.net"))

        ydl_opts = {
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'format': 'best[filesize<1000M]',
            'noplaylist': True,
            'quiet': True,
            'extractor_args': {
                'instagram': {'skip': ['auth']},
                'facebook': {'skip': ['auth']},
                'tiktok': {'skip': ['auth']}
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if info.get('filesize', 0) > MAX_FILE_SIZE:
                await msg.edit_text(LANGUAGES[lang]['size_exceeded'])
                return

            file_path = ydl.prepare_filename(info)
            
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="upload_video"
            )
            
            with open(file_path, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=video_file,
                    caption=LANGUAGES[lang]['success'],
                    supports_streaming=True,
                    read_timeout=120,
                    write_timeout=120,
                    connect_timeout=120
                )
        
        await msg.delete()
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        await msg.edit_text(f"{LANGUAGES[lang]['error']} {str(e)}")
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

# Flask Routes
@app.route('/')
def home():
    return jsonify({"status": "active", "service": "Advanced Video Downloader"})

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "version": "2.0"})

# Bot Setup
async def run_bot():
    application = ApplicationBuilder() \
        .token(TOKEN) \
        .post_init(disable_signals) \
        .build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    
    await application.run_polling()

async def disable_signals(app):
    """Disable signal handling in non-main threads"""
    app.updater.running = True

def run_flask_server():
    """Run Flask with production settings"""
    serve(app, host="0.0.0.0", port=PORT, threads=4)

if __name__ == '__main__':
    # Create downloads directory
    os.makedirs("downloads", exist_ok=True)
    
    # Start Flask in a daemon thread
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    
    # Run bot in main thread with proper signal handling
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        logger.info(f"🚀 Starting bot on port {PORT}")
        loop.run_until_complete(run_bot())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
        logger.info("🛑 Bot stopped gracefully")
