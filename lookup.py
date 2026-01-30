import asyncio
import logging
from datetime import datetime
from typing import Dict
import aiohttp
import json
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ========== FORCE JOIN CHANNELS ==========
FORCE_CHANNELS = ["@lolspot", "@APNA_WORLD1"]

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

APIS = {
    "phone": {
        "name": "📱 Phone Number",
        "endpoint": "https://veerulookup.onrender.com/search_phone?number=",
        "example": "9876543210",
        "validation": r'^[0-9]{10}$',
        "emoji": "📱"
    },
    "aadhaar": {
        "name": "🆔 Aadhaar Card",
        "endpoint": "https://veerulookup.onrender.com/search_aadhaar?aadhaar=",
        "example": "123456789012",
        "validation": r'^[0-9]{12}$',
        "emoji": "🆔"
    },
    "gst": {
        "name": "🏢 GST Number",
        "endpoint": "https://veerulookup.onrender.com/search_gst?gst=",
        "example": "27ABCDE1234F1Z5",
        "validation": r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$',
        "emoji": "🏢"
    },
    "upi": {
        "name": "💸 UPI ID",
        "endpoint": "https://veerulookup.onrender.com/search_upi?upi=",
        "example": "username@bank",
        "validation": r'^[a-zA-Z0-9._-]+@[a-zA-Z0-9]+$',
        "emoji": "💸"
    },
    "ifsc": {
        "name": "🏦 IFSC Code",
        "endpoint": "https://veerulookup.onrender.com/search_ifsc?ifsc=",
        "example": "SBIN0001234",
        "validation": r'^[A-Z]{4}0[A-Z0-9]{6}$',
        "emoji": "🏦"
    },
    "pincode": {
        "name": "📮 Pincode",
        "endpoint": "https://veerulookup.onrender.com/search_pincode?pincode=",
        "example": "110001",
        "validation": r'^[0-9]{6}$',
        "emoji": "📮"
    },
    "vehicle": {
        "name": "🚗 Vehicle RC",
        "endpoint": "https://veerulookup.onrender.com/search_vehicle?rc=",
        "example": "UP32QP0001",
        "validation": r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{1,4}$',
        "emoji": "🚗"
    }
}

user_sessions = {}

BOT_CREDITS = """
🤖 *Multi-Service Lookup Bot*
━━━━━━━━━━━━━━━━━━━━
👨‍💻 Developer: Sohman
"""

# ========== FORCE JOIN CHECK ==========
async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    for channel in FORCE_CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    joined = await check_join(update, context)

    if not joined:
        keyboard = [
            [InlineKeyboardButton("🔔 Join Channel 1", url="https://t.me/lolspot")],
            [InlineKeyboardButton("🔔 Join Channel 2", url="https://t.me/APNA_WORLD1")],
            [InlineKeyboardButton("✅ Joined", callback_data="check_join")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "⚠️ Bot use karne ke liye pehle dono channel join karo:",
            reply_markup=reply_markup
        )
        return

    user = update.effective_user
    welcome_text = f"""
👋 Hello *{user.first_name}*! 

{BOT_CREDITS}

👇 *Select a lookup type below:*"""
    
    keyboard = [
        [InlineKeyboardButton("📱 Phone Number", callback_data='phone')],
        [InlineKeyboardButton("🆔 Aadhaar Card", callback_data='aadhaar')],
        [InlineKeyboardButton("🏢 GST Number", callback_data='gst')],
        [InlineKeyboardButton("💸 UPI ID", callback_data='upi')],
        [InlineKeyboardButton("🏦 IFSC Code", callback_data='ifsc')],
        [InlineKeyboardButton("📮 Pincode", callback_data='pincode')],
        [InlineKeyboardButton("🚗 Vehicle RC", callback_data='vehicle')],
        [InlineKeyboardButton("ℹ️ Help", callback_data='help'),
         InlineKeyboardButton("📊 Stats", callback_data='stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)


async def join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    joined = await check_join(update, context)

    if joined:
        await query.edit_message_text("✅ Thanks! Ab /start likho.")
    else:
        await query.answer("❌ Pehle dono channel join karo!", show_alert=True)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "check_join":
        await join_callback(update, context)
        return

    if data in APIS:
        user_sessions[user_id] = data
        api_info = APIS[data]
        await query.edit_message_text(
            f"{api_info['emoji']} *Enter {api_info['name']}*\nExample: `{api_info['example']}`",
            parse_mode="Markdown"
        )

    elif data == "back":
        await start(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_input = update.message.text.strip()

    if user_id not in user_sessions:
        await update.message.reply_text("Use /start first")
        return

    lookup_type = user_sessions[user_id]
    api_info = APIS[lookup_type]

    if not re.match(api_info['validation'], user_input):
        await update.message.reply_text("❌ Invalid format")
        return

    await update.message.reply_text("⏳ Processing...")
    result = await perform_lookup(lookup_type, user_input)

    await update.message.reply_text(json.dumps(result, indent=2))


async def perform_lookup(lookup_type: str, value: str) -> Dict:
    api_info = APIS[lookup_type]
    url = api_info['endpoint'] + value

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            return data


def main() -> None:
    BOT_TOKEN = "8228102952:AAFX6WyNSXou9xo0rFwRPh4zhRjPrgK7axs"

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot Started")
    application.run_polling()


if __name__ == '__main__':
    main()