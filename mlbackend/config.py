import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ── Supabase ──────────────────────────────────────────────
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # ── Weather (OpenWeather) ─────────────────────────────────
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")

    # ── Telegram Bot ──────────────────────────────────────────
    # Get from @BotFather on Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # ── WhatsApp (Meta Cloud API) ────────────────────────────
    # Get from https://developers.facebook.com/
    META_WHATSAPP_TOKEN: str = os.getenv("META_WHATSAPP_TOKEN", "")
    META_PHONE_NUMBER_ID: str = os.getenv("META_PHONE_NUMBER_ID", "")
    META_WEBHOOK_VERIFY_TOKEN: str = os.getenv("META_WEBHOOK_VERIFY_TOKEN", "agrisaathi_secret_token")

    # ── LLMs (Groq) ───────────────────────────────────────────
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")



    # ── Internal ──────────────────────────────────────────────
    MODEL_PATH: str = "model.joblib"
    PORT: int = 8000

    class Config:
        env_file = ".env"

settings = Settings()
