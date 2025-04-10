from supabase import create_client
import os

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(url, key)

def check_and_decrement_balance(telegram_id):
    user = supabase.table("users").select("doc_balance").eq("telegram_id", str(telegram_id)).single().execute().data
    if not user:
        return False, "User not found."
    current_balance = user.get("doc_balance", 0)
    if current_balance < 1:
        return False, "⚠️ You have no credits. Use /addfunds to purchase processing credits."
    # Deduct one credit
    supabase.table("users").update({"doc_balance": current_balance - 1}).eq("telegram_id", str(telegram_id)).execute()
    return True, f"✅ Remaining balance: {current_balance - 1}"