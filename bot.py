import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

load_dotenv()
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

CATEGORIES = {
    "website": "💡 Идеи для сайта",
    "prizes": "🎁 Призы (магазин/колесо)",
    "songs": "🎵 Предложения по песням",
    "games": "🎮 Предложения по играм",
    "bugs": "🐛 Баги и проблемы",
    "other": "📝 Другое"
}

user_states = {}
DATA_FILE = "suggestions.json"

def load_data():
    if not os.path.exists(DATA_FILE): return []
    with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_states[update.message.chat_id] = None
    keyboard = [
        [InlineKeyboardButton(CATEGORIES["website"], callback_data="website"), InlineKeyboardButton(CATEGORIES["prizes"], callback_data="prizes")],
        [InlineKeyboardButton(CATEGORIES["songs"], callback_data="songs"), InlineKeyboardButton(CATEGORIES["games"], callback_data="games")],
        [InlineKeyboardButton(CATEGORIES["bugs"], callback_data="bugs"), InlineKeyboardButton(CATEGORIES["other"], callback_data="other")]
    ]
    await update.message.reply_text("Привет! ☀️ Выбери категорию, чтобы оставить предложение:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    category = query.data
    user_states[chat_id] = category
    await query.edit_message_text(f"Категория: *{CATEGORIES[category]}*\n\nНапиши своё предложение или опиши, что не так:", parse_mode="Markdown")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id not in user_states or user_states[chat_id] is None:
        await update.message.reply_text("Сначала нажми /start и выбери категорию.")
        return
    category = user_states[chat_id]
    text = update.message.text
    username = update.message.from_user.full_name
    entry = {"date": datetime.now().isoformat(), "user": username, "category": CATEGORIES[category], "text": text}
    data = load_data()
    data.append(entry)
    save_data(data)
    try:
        msg = f"📝 *Новое предложение*\n\n👤 {username}\n📂 Категория: {CATEGORIES[category]}\n💬 Текст:\n```{text}```"
        await context.bot.send_message(chat_id=OWNER_ID, text=msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление: {e}")
    del user_states[chat_id]
    await update.message.reply_text("Спасибо тебе, мое солнышко, я очень постараюсь это добавить/исправить в ближайшее время 💖")

def main():
    if not BOT_TOKEN or not OWNER_ID:
        raise ValueError("Проверь .env файл: BOT_TOKEN и OWNER_ID должны быть заполнены!")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_category))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("✅ Бот запущен! Ожидает сообщений...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()