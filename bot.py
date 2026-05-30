import os
import json
import logging
import threading
import asyncio
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ---------------- CONFIG ----------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

DATA_FILE = "suggestions.json"

CATEGORIES = {
    "website": "💡 Идеи для сайта",
    "prizes": "🎁 Призы",
    "songs": "🎵 Предложения по песням",
    "games": "🎮 Предложения по играм",
    "bugs": "🐞 Баги и проблемы",
    "other": "📝 Другое"
}

user_states = {}

# ---------------- STORAGE ----------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return []


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


# ---------------- HEALTH SERVER ----------------

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"alive")

    def log_message(self, *args):
        return


def run_health_server():
    port = int(os.getenv("PORT", 8080))

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    server.serve_forever()


# ---------------- UI ----------------

async def show_menu(update, context):
    chat_id = update.effective_chat.id

    user_states[chat_id] = None

    keyboard = [
        [
            InlineKeyboardButton(
                CATEGORIES["website"],
                callback_data="website"
            ),
            InlineKeyboardButton(
                CATEGORIES["prizes"],
                callback_data="prizes"
            )
        ],
        [
            InlineKeyboardButton(
                CATEGORIES["songs"],
                callback_data="songs"
            ),
            InlineKeyboardButton(
                CATEGORIES["games"],
                callback_data="games"
            )
        ],
        [
            InlineKeyboardButton(
                CATEGORIES["bugs"],
                callback_data="bugs"
            ),
            InlineKeyboardButton(
                CATEGORIES["other"],
                callback_data="other"
            )
        ]
    ]

    await update.effective_message.reply_text(
        "Привет ☀️\nВыбери категорию:",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


async def start(update, context):
    await show_menu(update, context)


async def menu(update, context):
    await show_menu(update, context)


async def category(update, context):
    query = update.callback_query

    await query.answer()

    chat_id = query.message.chat.id

    user_states[chat_id] = query.data

    await query.edit_message_text(
        f"{CATEGORIES[query.data]}\n\nНапиши предложение 👇"
    )


async def text_handler(update, context):
    chat_id = update.effective_chat.id

    if (
        chat_id not in user_states
        or user_states[chat_id] is None
    ):
        await show_menu(update, context)
        return

    selected = user_states[chat_id]

    entry = {
        "date": datetime.now().isoformat(),
        "user": update.effective_user.full_name,
        "category": CATEGORIES[selected],
        "text": update.message.text
    }

    data = load_data()

    data.append(entry)

    save_data(data)

    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=(
                "📝 Новое предложение\n\n"
                f"👤 {entry['user']}\n"
                f"📂 {entry['category']}\n"
                f"💬 {entry['text']}"
            )
        )

    except Exception:
        logger.exception(
            "Owner notification error"
        )

    user_states.pop(chat_id, None)

    await update.message.reply_text(
        "Спасибо 💖\n\nЧтобы отправить ещё — /menu"
    )


async def error_handler(update, context):
    logger.exception(context.error)


# ---------------- MAIN ----------------

def main():

    if not BOT_TOKEN:
        raise ValueError(
            "BOT_TOKEN missing"
        )

    if OWNER_ID == 0:
        raise ValueError(
            "OWNER_ID missing"
        )

    threading.Thread(
        target=run_health_server,
        daemon=True
    ).start()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "menu",
            menu
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            category
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    app.add_error_handler(
        error_handler
    )

    logger.info(
        "Bot started successfully"
    )

    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        close_loop=False
    )


if __name__ == "__main__":
    main()
