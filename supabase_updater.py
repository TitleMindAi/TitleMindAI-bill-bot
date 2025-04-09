from supabase import create_client
import os

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(url, key)

def update_user_balance(telegram_id, amount):
    user = supabase.table("users").select("*").eq("telegram_id", telegram_id).single().execute().data
    new_balance = user["doc_balance"] + int(amount / 3)  # $3 = 1 doc
    supabase.table("users").update({"doc_balance": new_balance}).eq("telegram_id", telegram_id).execute()