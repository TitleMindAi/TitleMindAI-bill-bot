import os
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from dotenv import load_dotenv
from supabase import create_client

from upload_handler import save_uploaded_file
from ocr_engine import extract_text_from_pdf
from parser import parse_lease_text_to_fields
from formatter import write_to_tsv
from payment_handler import create_checkout_session

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

app = Flask(__name__)
user_sessions = {}

def send_payment_options(chat_id):
    base_url = "https://titlemind-ai-bill-bot.onrender.com/thankyou"
    cancel_url = "https://titlemind.ai"

    one_doc = create_checkout_session("prod_S60geJuhqiu443", chat_id, base_url, cancel_url)
    bulk_credits = create_checkout_session("prod_S6PNByjSPapXYG", chat_id, base_url, cancel_url)
    one_dollar = create_checkout_session("prod_S6PPodvScaPPHK", chat_id, base_url, cancel_url)

    keyboard = [
        [InlineKeyboardButton("💳 Process 1 Doc ($3)", url=one_doc)],
        [InlineKeyboardButton("💳 Add 105 Credits ($60)", url=bulk_credits)],
        [InlineKeyboardButton("💳 Add 1 Credit ($1)", url=one_dollar)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.send_message(chat_id=chat_id, text="💳 Choose a payment option below:", reply_markup=reply_markup)

def deduct_user_credits(telegram_id, amount=3):
    user = supabase.table("users").select("doc_balance").eq("telegram_id", str(telegram_id)).single().execute().data
    if not user:
        return False, "⚠️ User not found."
    current_balance = user.get("doc_balance", 0)
    if current_balance < amount:
        return False, f"🚫 You need {amount} credits to process a document. Use /addfunds to reload."
    supabase.table("users").update({"doc_balance": current_balance - amount}).eq("telegram_id", str(telegram_id)).execute()
    return True, f"✅ {amount} credits deducted. Remaining: {current_balance - amount}"

def process_upload(chat_id, context: CallbackContext, headers: list):
    ok, msg = deduct_user_credits(chat_id, amount=3)
    if not ok:
        bot.send_message(chat_id=chat_id, text=msg)
        return

    file = context.user_data["pending_file"]
    file_id = file.file_id
    file_name = file.file_name

    new_file = bot.get_file(file_id)
    file_bytes = new_file.download_as_bytearray()
    local_path = save_uploaded_file(file_bytes, file_name)

    text = extract_text_from_pdf(local_path)
    data_rows = parse_lease_text_to_fields(text)

    output_filename = f"output_{file_id}.tsv"
    output_path = write_to_tsv(data_rows, headers, output_filename)

    with open(output_path, "rb") as f:
        bot.send_document(chat_id=chat_id, document=f)

def get_user_balance(telegram_id):
    user = supabase.table("users").select("doc_balance").eq("telegram_id", str(telegram_id)).single().execute().data
    return user["doc_balance"] if user else 0

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def respond():
    update = Update.de_json(request.get_json(force=True), bot)
    chat_id = update.message.chat.id
    message_text = update.message.text if update.message else ""

    context = CallbackContext(bot)
    context.user_data = user_sessions.setdefault(chat_id, {})

    if update.message.document:
        context.user_data["pending_file"] = update.message.document
        bot.send_message(
            chat_id=chat_id,text="📂 File received!")

📋 Now please paste your Excel column headers (copied from Excel)."
        )

    elif "	" in message_text:
        headers = message_text.strip().split("	")
        context.user_data["headers"] = headers
        if "pending_file" in context.user_data:
            keyboard = [[InlineKeyboardButton("🧾 Build My Runsheet", callback_data="build_runsheet")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            bot.send_message(
                chat_id=chat_id,
                text="✅ Headers saved.
Tap below to build your runsheet.",
                reply_markup=reply_markup
            )
        else:
            bot.send_message(chat_id=chat_id, text="⚠️ Upload a file first.")

    elif message_text == "/start":
        existing = supabase.table("users").select("telegram_id").eq("telegram_id", str(chat_id)).execute().data
        if not existing:
            supabase.table("users").insert({"telegram_id": str(chat_id), "doc_balance": 3}).execute()
            bot.send_message(
                chat_id=chat_id,
                text="👋 Welcome to TitleMind AI!

You’ve been granted 3 free credits to try it out.

Upload a lease and paste your headers to begin."
            )
        else:
            bot.send_message(
                chat_id=chat_id,
                text="👋 Welcome back to TitleMind AI.

Upload your lease, then paste your headers."
            )

    elif message_text == "/reset_headers":
        context.user_data.pop("pending_file", None)
        context.user_data.pop("headers", None)
        bot.send_message(chat_id=chat_id, text="🧼 File and header memory cleared.")

    elif message_text == "/help":
        bot.send_message(
            chat_id=chat_id,
            text="📋 Upload a lease → paste headers → tap 🧾 Build My Runsheet.

Use /addfunds to purchase processing credits."
        )

    elif message_text == "/balance":
        balance = get_user_balance(chat_id)
        bot.send_message(chat_id=chat_id, text=f"💳 You currently have {balance} credits available.")

    elif message_text == "/addfunds":
        send_payment_options(chat_id)

    else:
        if not context.user_data.get("pending_file") and not "	" in message_text:
            bot.send_message(chat_id=chat_id, text="🧾 Got it. If that was a document, paste your headers next. Otherwise, upload your lease.")

    return "ok"

@app.route(f"/{TELEGRAM_TOKEN}/callback", methods=["POST"])
def respond_callback():
    update = Update.de_json(request.get_json(force=True), bot)
    query = update.callback_query
    chat_id = query.message.chat.id
    context = CallbackContext(bot)
    context.user_data = user_sessions.setdefault(chat_id, {})

    if query.data == "build_runsheet":
        headers = context.user_data.get("headers")
        if "pending_file" in context.user_data and headers:
            process_upload(chat_id, context, headers)
            query.answer("🧾 Processing your file...")
        else:
            query.answer("⚠️ Missing file or headers. Upload and paste headers first.")
    return "ok"

@app.route("/")
def index():
    return "🧠 TitleMindBot is running."

if __name__ == "__main__":
    print("🚀 Flask server starting...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
