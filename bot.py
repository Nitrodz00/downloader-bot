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
import re

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
        'start': "🎬 **Ultimate Social Media Downloader**\n\n• Supports: Instagram, TikTok, Twitter/X, Facebook, YouTube, Reddit, Pinterest\n• Max size: 1000MB\n• Fast HD downloads",
        'processing': "⏳ Downloading your media...",
        'success': "✅ Download complete!",
        'error': "❌ Error:",
        'size_exceeded': "⚠️ File exceeds 1000MB limit",
        'unsupported': "🚫 Unsupported link type",
        'help': "🆘 Need help? Contact @YourSupport",
        'share': "📲 Share Bot",
        'cookies_needed': "🔒 Login required for this content"
    },
    'ar': {
        'start': "🎬 **بوت تحميل وسائل التواصل الاجتماعي**\n\n• يدعم: إنستجرام، تيك توك، تويتر/X، فيسبوك، يوتيوب، ريديت، بنترست\n• أقصى حجم: 1000 ميجابايت\n• تحميل سريع بجودة HD",
        'processing': "⏳ جاري تحميل الميديا...",
        'success': "✅ اكتمل التحميل بنجاح!",
        'error': "❌ حدث خطأ:",
        'size_exceeded': "⚠️ الملف يتجاوز حد 1000 ميجابايت",
        'unsupported': "🚫 نوع الرابط غير مدعوم",
        'help': "🆘 للمساعدة تواصل @الدعم_الفني",
        'share': "📲 مشاركة البوت",
        'cookies_needed': "🔒 يلزم تسجيل الدخول لهذا المحتوى"
    }
}

def detect_language(update: Update) -> str:
    return 'ar' if update.effective_user and update.effective_user.language_code and 'ar' in update.effective_user.language_code else 'en'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = detect_language(update)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(LANGUAGES[lang]['share'], url="https://t.me/share/url?url=https://t.me/SpeedNitroDownload_bot")],
        [InlineKeyboardButton(LANGUAGES[lang]['help'], url="https://t.me/YourSupport")]
    ])
    await update.message.reply_text(LANGUAGES[lang]['start'], reply_markup=keyboard)

def normalize_url(url: str) -> str:
    """Normalize URLs for better compatibility"""
    url = url.replace("//x.com", "//twitter.com") \
             .replace("//www.x.com", "//twitter.com") \
             .replace("//m.x.com", "//mobile.twitter.com")
    
    # Remove tracking parameters
    url = re.sub(r'(\?|&)(utm_|si=|fbclid|igshid|feature)=[^&]+', '', url)
    url = url.replace('?&', '?').replace('&&', '&')
    if url.endswith('?'):
        url = url[:-1]
    
    return url

async def download_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = detect_language(update)
    original_url = update.message.text.strip()
    url = normalize_url(original_url)
    msg = await update.message.reply_text(LANGUAGES[lang]['processing'])
    
    try:
        ydl_opts = {
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'format': 'best[filesize<1000M]',
            'quiet': True,
            'no_check_certificate': True,
            'extractor_args': {
                'instagram': {'skip': ['auth']},
                'facebook': {'skip': ['auth']},
                'tiktok': {'skip': ['auth']},
                'twitter': {'skip': ['auth']}
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.google.com/'
            },
            'retries': 3,
            'fragment_retries': 3,
            'extract_flat': True
        }

        # Special handling for different platforms
        if 'instagram.com' in url:
            ydl_opts['extractor_args']['instagram']['skip'] = ['auth']
        elif 'tiktok.com' in url:
            ydl_opts['http_headers']['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
        elif 'twitter.com' in url or 'x.com' in url:
            ydl_opts['extractor_args']['twitter']['skip'] = ['auth']
            url = url.replace('x.com', 'twitter.com')

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if info.get('filesize', 0) > MAX_FILE_SIZE:
                await msg.edit_text(LANGUAGES[lang]['size_exceeded'])
                return

            file_path = ydl.prepare_filename(info)
            
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="upload_video" if info.get('ext') in ['mp4', 'mov'] else "upload_document"
            )
            
            with open(file_path, 'rb') as media_file:
                if info.get('ext') in ['mp4', 'mov']:
                    await context.bot.send_video(
                        chat_id=update.effective_chat.id,
                        video=media_file,
                        caption=LANGUAGES[lang]['success'],
                        supports_streaming=True,
                        read_timeout=120,
                        write_timeout=120,
                        connect_timeout=120
                    )
                else:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=media_file,
                        caption=LANGUAGES[lang]['success']
                    )
        
        await msg.delete()
    except yt_dlp.utils.DownloadError as e:
        if 'requires login' in str(e).lower():
            await msg.edit_text(f"{LANGUAGES[lang]['cookies_needed']}\n{LANGUAGES[lang]['error']} {str(e)}")
        else:
            await msg.edit_text(f"{LANGUAGES[lang]['error']} {str(e)}")
        logger.error(f"Download error: {str(e)}")
    except Exception as e:
        await msg.edit_text(f"{LANGUAGES[lang]['error']} {str(e)}")
        logger.error(f"Unexpected error: {str(e)}")
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

# Flask Routes
@app.route('/')
def home():
    return jsonify({"status": "active", "service": "Universal Social Media Downloader"})

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "version": "3.0"})

def run_flask():
    """Run Flask server"""
    logger.info(f"🌐 Starting Flask server on port {PORT}")
    serve(app, host="0.0.0.0", port=PORT, threads=4)

def run_bot():
    """Run Telegram bot with proper event loop"""
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & (
            filters.Entity("url") | filters.Entity("text_link") |
            filters.Regex(r'https?://(www\.)?(instagram|tiktok|twitter|x|facebook|youtube|reddit|pinterest)\.')
        ),
        download_media
    ))
    
    logger.info("🤖 Starting Telegram Bot")
    application.run_polling()

if __name__ == '__main__':
    # Create downloads directory
    os.makedirs("downloads", exist_ok=True)
    
    # Start Flask in a thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Run bot in main thread (required for Windows compatibility)
    run_bot()
