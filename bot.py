import os
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
from waitress import serve  # إضافة خادم إنتاجي

# Flask App Setup
app = Flask(__name__)

# Load Environment Variables
TOKEN = os.getenv("TELEGRAM_TOKEN")

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
        
        ydl_opts = {
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'format': 'best[filesize<50M]',
            'cookiefile': 'cookies.txt',
            'extractor_args': {
                'instagram': {'skip_auth': False},
                'facebook': {'credentials': {'email': os.getenv('FB_EMAIL'), 'password': os.getenv('FB_PASSWORD')}},
                'twitter': {'username': os.getenv('TWITTER_USER'), 'password': os.getenv('TWITTER_PASS')}
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=open(file_path, 'rb'),
                caption=f"✅ {info.get('title', '')}",
                supports_streaming=True
            )
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ: {str(e)}")
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

# Flask Routes
@app.route('/')
def home():
    return "Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        update = Update.de_json(request.get_json(), bot_app.bot)
        bot_app.dispatcher.process_update(update)
        return jsonify(status="ok"), 200
    return jsonify(status="Method not allowed"), 405

# Initialize Telegram Bot
def setup_bot():
    os.makedirs("downloads", exist_ok=True)
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    
    return application

if __name__ == '__main__':
    # Initialize bot components
    bot_app = setup_bot()
    
    # Start production server
    serve(app, host='0.0.0.0', port=8080)
