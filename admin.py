import os
from flask import Flask, request, jsonify
from supabase import create_client

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

@app.route("/admin/users", methods=["GET"])
def list_users():
    res = supabase.table("users").select("telegram_id, doc_balance").execute()
    return jsonify(res.data)

@app.route("/admin/update_balance", methods=["POST"])
def update_user():
    data = request.json
    telegram_id = data.get("telegram_id")
    new_balance = data.get("balance")
    if not telegram_id or new_balance is None:
        return jsonify({"error": "Missing telegram_id or balance"}), 400
    supabase.table("users").update({"doc_balance": int(new_balance)}).eq("telegram_id", str(telegram_id)).execute()
    return jsonify({"status": "updated", "telegram_id": telegram_id, "new_balance": new_balance})