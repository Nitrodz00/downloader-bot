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

# Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Security Warning: Never expose real token in code!
TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")  # Replace with your token
PORT = int(os.getenv("PORT", 8080))
MAX_FILE_SIZE = 1000 * 1024 * 1024  # 1000MB

# Multi-language support
LANGUAGES = {
    'en': {
        'start': "🎬 **Video Download Bot**\n\nSend me a video link from:\nInstagram, TikTok, Twitter, Facebook\n\nMax size: 1000MB",
        'processing': "⏳ Downloading your video...",
        'success': "✅ Download complete!",
        'error': "❌ Error:",
        'size_exceeded': "⚠️ File exceeds 1000MB limit",
        'unsupported': "🚫 Unsupported link",
        'help': "🆘 Need help? Contact @YourSupport"
    },
    'ar': {
        'start': "🎬 **بوت تحميل الفيديوهات**\n\nأرسل رابط فيديو من:\nإنستجرام، تيك توك، تويتر، فيسبوك\n\nأقصى حجم: 1000 ميجابايت",
        'processing': "⏳ جاري تحميل الفيديو...",
        'success': "✅ اكتمل التحميل!",
        'error': "❌ خطأ:",
        'size_exceeded': "⚠️ الملف يتجاوز حد 1000 ميجابايت",
        'unsupported': "🚫 الرابط غير مدعوم",
        'help': "🆘 للمساعدة تواصل @الدعم_الفني"
    }
}

# Utility functions
def detect_language(update: Update) -> str:
    return 'ar' if update.effective_user.language_code and 'ar' in update.effective_user.language_code else 'en'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = detect_language(update)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(LANGUAGES[lang]['help'], url="https://t.me/YourSupport")]
    ])
    await update.message.reply_text(LANGUAGES[lang]['start'], reply_markup=keyboard)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = detect_language(update)
    url = update.message.text.strip()
    
    # Validate URL
    if not any(domain in url for domain in ['instagram', 'tiktok', 'twitter', 'x.com', 'facebook']):
        await update.message.reply_text(LANGUAGES[lang]['unsupported'])
        return

    msg = await update.message.reply_text(LANGUAGES[lang]['processing'])
    
    try:
        # Mobile-friendly URL conversion
        url = (url.replace("instagram.com", "ddinstagram.com")
                .replace("x.com", "fxtwitter.com")
                .replace("twitter.com", "fxtwitter.com")
                .replace("tiktok.com", "tiktx.com")
                .replace("facebook.com", "fdown.net"))

        ydl_opts = {
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'format': 'best',
            'max_filesize': MAX_FILE_SIZE,
            'noplaylist': True,
            'quiet': True,
            'extractor_args': {
                'instagram': {'skip': ['auth']},
                'facebook': {'skip': ['auth']},
                'tiktok': {'skip': ['auth']}
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
        logger.error(f"Error: {str(e)}")
        await msg.edit_text(f"{LANGUAGES[lang]['error']} {str(e)}")
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

# Flask Routes
@app.route('/')
def home():
    return jsonify({"status": "active", "service": "Telegram Video Downloader"})

@app.route('/health')
def health_check():
    return jsonify({"status": "ok"})

# Bot Setup
async def run_bot():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await application.run_polling()

def setup_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())

def run_flask():
    serve(app, host="0.0.0.0", port=PORT, threads=4)

if __name__ == '__main__':
    # Create downloads directory
    os.makedirs("downloads", exist_ok=True)
    
    # Start threads
    threading.Thread(target=setup_bot, daemon=True).start()
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Keep application running
    logger.info(f"🚀 Bot started on port {PORT}")
    while True:
        pass
