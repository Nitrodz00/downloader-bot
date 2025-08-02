import sys
from telegram.error import Conflict

try:
    # ... باقي الكود ...
except Conflict as e:
    print("⚠️ خطأ: البوت يعمل بالفعل في مكان آخر!")
    sys.exit(1)
    import os
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("شارك البوت 📣", url="https://t.me/share/url?url=https://t.me/AllDownloadspeed_bot")],
    ])
    await update.message.reply_text(
        "👋 مرحباً! أرسل رابط فيديو وسأقوم بتحميله لك.",
        reply_markup=keyboard
    )

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 فقط أرسل رابط فيديو من تيك توك أو إنستغرام أو فيسبوك أو تويتر، وسأقوم بتحميله لك 🔽"
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "help":
        await help_handler(update, context)

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    msg = await update.message.reply_text("⏳ جاري التحميل...")

    ydl_opts = {
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'format': 'bestvideo+bestaudio/best',
        'noplaylist': True,
        'quiet': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        if os.path.getsize(file_path) > 48 * 1024 * 1024:
            await msg.edit_text("❌ الحجم أكبر من 50MB.")
            os.remove(file_path)
            return

        with open(file_path, "rb") as f:
            await context.bot.send_video(chat_id=update.effective_chat.id, video=f)
        await msg.delete()
        os.remove(file_path)

    except Exception as e:
        await msg.edit_text(f"⚠️ فشل التحميل: {e}")

if __name__ == '__main__':
    os.makedirs("downloads", exist_ok=True)
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

    print("✅ البوت يعمل الآن...")
    
    # استبدال هذا الجزء:
    # app.run_polling(
    #     host="0.0.0.0",
    #     port=PORT,
    #     webhook_url=None
    # )
    
    # بهذا:
    app.run_polling()
