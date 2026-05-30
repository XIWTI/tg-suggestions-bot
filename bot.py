import os
import json
import logging
import asyncio
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

CATEGORIES = {
    "website": "💡 Идеи для сайта",
    "prizes": "🎁 Призы (магазин/колесо)",
    "songs": "🎵 Предложения по песням",
    "games": "🎮 Предложения по играм",
    "bugs": " Баги и проблемы",
    "other": "📝 Другое"
}

user_states = {}
DATA_FILE = "suggestions.json"

def load_data():
    if not os.path.exists(DATA_FILE): return []
    with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_states[update.message.chat_id] = None
    keyboard = [
        [InlineKeyboardButton(CATEGORIES["website"], callback_data="website"), InlineKeyboardButton(CATEGORIES["prizes"], callback_data="prizes")],
        [InlineKeyboardButton(CATEGORIES["songs"], callback_data="songs"), InlineKeyboardButton(CATEGORIES["games"], callback_data="games")],
        [InlineKeyboardButton(CATEGORIES["bugs"], callback_data="bugs"), InlineKeyboardButton(CATEGORIES["other"], callback_data="other")]
    ]
    await update.message.reply_text("Привет! ☀️ Выбери категорию, чтобы оставить предложение:", reply_markup=InlineKeyboardMarkup(keyboard))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): await show_menu(update, context)
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE): await show_menu(update, context)

async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_states[query.message.chat_id] = query.data
    await query.edit_message_text(f"Категория: *{CATEGORIES[query.data]}*\n\nНапиши своё предложение:", parse_mode="Markdown")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id not in user_states or user_states[chat_id] is None:
        await show_menu(update, context)
        return
    
    category = user_states[chat_id]
    text = update.message.text
    username = update.message.from_user.full_name
    
    data = load_data()
    data.append({"date": datetime.now().isoformat(), "user": username, "category": CATEGORIES[category], "text": text})
    save_data(data)
    
    try:
        await context.bot.send_message(chat_id=OWNER_ID, text=f"📝 *Новое предложение*\n\n👤 {username}\n📂 {CATEGORIES[category]}\n💬 ```{text}```", parse_mode="Markdown")
    except Exception as e: logger.error(e)
    
    del user_states[chat_id]
    await update.message.reply_text("Спасибо тебе, мое солнышко! 💖\n\nЧтобы добавить ещё одно, напиши /menu 👇")
    await show_menu(update, context)

def main():
    if not BOT_TOKEN or not OWNER_ID: raise ValueError("Check env vars!")

    # Health Check Server for Render
    class H(BaseHTTPRequestHandler):
        def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
        def log_message(self, format, *args): pass
    def run_h(): HTTPServer(('', 8080), H).serve_forever()
    threading.Thread(target=run_h, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CallbackQueryHandler(handle_category))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("✅ Bot started...")
    
    async def main_async():
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()

    try: asyncio.run(main_async())
    except KeyboardInterrupt: pass
    finally:
        if app.running: app.stop(); app.shutdown()

if __name__ == "__main__": main()