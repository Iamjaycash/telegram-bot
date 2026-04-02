import os
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import json

# Flask app to keep Render happy
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health():
    return "OK"

TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    print("ERROR: BOT_TOKEN environment variable not set!")
    exit(1)

DATA_FILE = "users.json"

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        users = json.load(f)
else:
    users = {}

def save_users():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=2)

def is_nigerian_number(phone):
    phone = phone.replace(" ", "").replace("-", "").replace("+", "")
    return phone.startswith("234") or phone.startswith("0")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in users:
        users[user_id] = {
            "step": "awaiting_phone",
            "phone": None,
            "referral_code": f"REF{user_id[-5:]}",
            "earnings": 0,
            "referred_by": None
        }
        save_users()
        
        keyboard = [[{"text": "Send my phone number", "request_contact": True}]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "🇳🇬 Welcome! Nigeria Only.\n\nTap the button below to share your Nigerian phone number.",
            reply_markup=reply_markup
        )
    else:
        code = users[user_id]["referral_code"]
        await update.message.reply_text(f"Welcome back!\n\nYour referral code: `{code}`\nSend /earnings to see your points.", parse_mode="Markdown")

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    contact = update.message.contact
    phone = contact.phone_number
    
    if not is_nigerian_number(phone):
        await update.message.reply_text("❌ Sorry, only Nigerian phone numbers (+234) are allowed.")
        return
    
    users[user_id]["phone"] = phone
    users[user_id]["step"] = "verified"
    save_users()
    
    code = users[user_id]["referral_code"]
    await update.message.reply_text(
        f"✅ Nigerian number verified!\n\nYour referral code: `{code}`\n\nShare this code with friends. When they join, you earn 10 points!\n\nSend /earnings to check your balance.",
        parse_mode="Markdown"
    )

async def earnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in users:
        points = users[user_id]["earnings"]
        code = users[user_id]["referral_code"]
        await update.message.reply_text(f"💰 Your points: {points}\n\nYour referral code: `{code}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("Send /start first")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    msg = update.message.text
    print(f"\n📩 Message from {user_id}: {msg}\n")
    await update.message.reply_text("✅ Message received. Admin will reply soon.")

def run_bot():
    bot_app = Application.builder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("earnings", earnings))
    bot_app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Bot is running...")
    bot_app.run_polling()

if __name__ == "__main__":
    # Run bot in background thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # Run Flask on Render's port
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
