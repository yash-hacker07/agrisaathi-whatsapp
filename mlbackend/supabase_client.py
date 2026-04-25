"""
AgriSaathi — Supabase DB Client
===============================
Handles saving and retrieving chat history for the WhatsApp Bot.
"""
from supabase import create_client, Client
from typing import List, Dict, Optional
from .config import settings

# Initialize client only if URL and KEY are provided
supabase: Optional[Client] = None
if settings.SUPABASE_URL and settings.SUPABASE_KEY:
    try:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    except Exception as e:
        print(f"Failed to initialize Supabase: {e}")

def log_message(phone_number: str, role: str, message_type: str, content: str):
    """
    Logs a message to the chat_history table.
    role: 'user' or 'bot'
    message_type: 'text', 'image', 'location'
    """
    if not supabase:
        print(f"Simulation Mode [DB Log]: {role} ({phone_number}) sent {message_type}: {content}")
        return
        
    try:
        data = {
            "phone_number": phone_number,
            "role": role,
            "message_type": message_type,
            "content": content
        }
        supabase.table("chat_history").insert(data).execute()
    except Exception as e:
        print(f"Error logging to Supabase: {e}")

def get_chat_history(phone_number: str, limit: int = 10) -> List[Dict]:
    """
    Retrieves the last N messages for a specific phone number, sorted by oldest to newest.
    """
    if not supabase:
        return [{"role": "bot", "content": "Simulation Mode: Supabase is not configured, so no chat history is available."}]
        
    try:
        response = supabase.table("chat_history") \
            .select("*") \
            .eq("phone_number", phone_number) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
            
        # Reverse the list so it's in chronological order (oldest first)
        history = response.data[::-1]
        return history
    except Exception as e:
        print(f"Error fetching from Supabase: {e}")
        return []

def format_chat_history(history: List[Dict]) -> str:
    """Formats the raw DB response into a readable string for WhatsApp."""
    if not history:
        return "No chat history found."
        
    formatted = "🕒 *Your Recent Chat History:*\n\n"
    for msg in history:
        role = "🧑 You" if msg["role"] == "user" else "🤖 Bot"
        content = msg["content"]
        if msg["message_type"] != "text":
            content = f"[{msg['message_type'].upper()}] {content}"
            
        # Truncate content if it's too long
        if len(content) > 100:
            content = content[:97] + "..."
            
        formatted += f"*{role}:* {content}\n\n"
        
    return formatted.strip()
