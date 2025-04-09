import os
from flask import Flask, request
import telegram
from dotenv import load_dotenv
from upload_handler import save_uploaded_file
from ocr_engine import extract_text_from_pdf
from parser import parse_lease_text_to_fields
from formatter import write_to_tsv
from bot_responder import simulate_bot_reply

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telegram.Bot(token=TELEGRAM_TOKEN)

app = Flask(__name__)

def process_upload(update, context, headers):
    file = update.message.document
    file_name = file.file_name
    file_id = file.file_id

    # Step 1: Download the file
    new_file = context.bot.get_file(file_id)
    file_bytes = new_file.download_as_bytearray()
    local_path = save_uploaded_file(file_bytes, file_name)

    # Step 2: Run OCR
    text = extract_text_from_pdf(local_path)

    # Step 3: Parse fields from lease text
    data_rows = parse_lease_text_to_fields(text)

    # Step 4: Format TSV
    output_filename = f"output_{file_id}.tsv"
    output_path = write_to_tsv(data_rows, headers, output_filename)

    # Step 5: Send file back
    with open(output_path, "rb") as f:
        context.bot.send_document(chat_id=update.message.chat_id, document=f)

    simulate_bot_reply(output_path)

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def respond():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    chat_id = update.message.chat.id
    message_text = update.message.text if update.message else ""

    # Placeholder headers until user pastes or stores them
    headers = ["Records", "Book", "Page", "Entry No.", "Instrument Effective Date",
               "Instrument Record or File Date", "Instrument Type", "Grantor", "Grantee",
               "Notes/Comments", "Property Description"]

    if update.message.document:
        # Simulate payment check before processing (stub for now)
        print("📂 Document received. Processing...")
        process_upload(update, None, headers)
    elif message_text == "/start":
        bot.send_message(chat_id=chat_id, text="👋 Welcome to TitleMind AI. Please upload your first document.")
    elif message_text == "/reset_headers":
        bot.send_message(chat_id=chat_id, text="✅ Your saved Excel column headers have been cleared.")
    elif message_text == "/help":
        bot.send_message(chat_id=chat_id, text="📎 Upload a lease or title doc.\nPaste your Excel headers.\nSubmit special formatting requests.\nUse /balance or /subscribe anytime.")
    elif message_text == "/balance":
        bot.send_message(chat_id=chat_id, text="💳 You currently have $12.00 in processing balance.")
    elif message_text == "/addfunds":
        bot.send_message(chat_id=chat_id, text="To add funds, choose Stripe or BTC:\n[Stripe Link]\n[BTC Wallet Address]")
    elif message_text == "/subscribe":
        bot.send_message(chat_id=chat_id, text="📅 Unlimited plan: $750/month for up to 1,000 documents.\nSubscribe here: [Stripe Plan Link]")
    else:
        bot.send_message(chat_id=chat_id, text="🧾 Got it. If that was a document, we'll process it. Otherwise, please upload your file or paste your column headers.")

    return "ok"

@app.route("/")
def index():
    return "🧠 TitleMindBot is up and running."

if __name__ == "__main__":
    print("🚀 Flask server starting...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))