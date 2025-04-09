import os
import stripe
from flask import Flask, request, jsonify
from supabase_updater import update_user_balance

app = Flask(__name__)
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    event = None

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        telegram_id = session.get("metadata", {}).get("telegram_id")
        amount = int(session["amount_total"]) / 100.0
        if telegram_id:
            update_user_balance(telegram_id, amount)
    return jsonify(success=True)