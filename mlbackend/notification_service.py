"""
AgriSaathi Notification Service
Handles:
  1. Telegram Bot alerts (scheme notifications, disaster alerts)
  2. Twilio SMS alerts (scheme notifications, critical warnings)
  3. Twilio Voice Call alerts (disaster/emergency alerts only)
"""

import os
import requests
from pydantic import BaseModel
from typing import Optional
from .config import settings


# ============================================================
# SCHEMAS
# ============================================================

class FarmerContact(BaseModel):
    phone: str                      # E.164 format: +91XXXXXXXXXX
    telegram_chat_id: Optional[str] = None
    name: str = "Farmer"
    lang: str = "hi"

class NotificationPayload(BaseModel):
    farmer: FarmerContact
    alert_type: str                 # "scheme", "disaster", "market", "weather"
    title: str
    message: str
    severity: str = "INFO"          # "INFO", "WARNING", "CRITICAL"


# ============================================================
# TELEGRAM BOT SERVICE
# ============================================================

def send_telegram_message(chat_id: str, message: str) -> dict:
    """
    Sends a message to a Telegram user via the AgriSaathi Bot.
    Requires TELEGRAM_BOT_TOKEN in environment / config.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return {"success": False, "error": "TELEGRAM_BOT_TOKEN not configured"}

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"         # supports <b>, <i>, <code> formatting
    }

    try:
        resp = requests.post(url, json=payload, timeout=8)
        data = resp.json()
        if data.get("ok"):
            return {"success": True, "message_id": data["result"]["message_id"]}
        else:
            return {"success": False, "error": data.get("description", "Unknown")}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# TWILIO SMS SERVICE
# ============================================================

def send_sms_alert(to_phone: str, message: str) -> dict:
    """
    Sends an SMS to the farmer using Twilio Messaging API.
    Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER.
    """
    sid  = settings.TWILIO_ACCOUNT_SID
    auth = settings.TWILIO_AUTH_TOKEN
    from_number = settings.TWILIO_PHONE_NUMBER

    if not all([sid, auth, from_number]):
        return {"success": False, "error": "Twilio credentials not fully configured"}

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    try:
        resp = requests.post(
            url,
            auth=(sid, auth),
            data={
                "To": to_phone,
                "From": from_number,
                "Body": message
            },
            timeout=10
        )
        data = resp.json()
        if resp.status_code in (200, 201):
            return {"success": True, "sms_sid": data.get("sid")}
        else:
            return {"success": False, "error": data.get("message", "Twilio error")}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# TWILIO VOICE CALL SERVICE (Emergency / Disaster Alerts)
# ============================================================

def send_voice_call_alert(to_phone: str, message: str, lang: str = "hi") -> dict:
    """
    Initiates an automated voice call using Twilio TwiML.
    The message is spoken aloud via Text-to-Speech using dynamic voice models.
    """
    sid  = settings.TWILIO_ACCOUNT_SID
    auth = settings.TWILIO_AUTH_TOKEN
    from_number = settings.TWILIO_PHONE_NUMBER

    if not all([sid, auth, from_number]):
        return {"success": False, "error": "Twilio credentials not fully configured"}

    # Dynamic language mapping to AWS Polly Voices mapped by Twilio
    voice_map = {
        "hi": ("hi-IN", "Polly.Aditi"),
        "te": ("te-IN", "Polly.Shruti"),
        "ta": ("ta-IN", "Polly.Aditi"), 
        "en": ("en-IN", "Polly.Raveena"),
        "bn": ("bn-IN", "Polly.Aditi"), 
        "gu": ("gu-IN", "Polly.Aditi"),
    }
    
    lang_code, voice_model = voice_map.get(lang, ("hi-IN", "Polly.Aditi"))

    # TwiML: tell Twilio to speak this text when the farmer picks up
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="{lang_code}" voice="{voice_model}">
        {message}
    </Say>
    <Pause length="1"/>
    <Say language="{lang_code}" voice="{voice_model}">
        This message was delivered by AgriSaathi AI. Please take immediate precautions.
    </Say>
</Response>"""

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json"
    try:
        resp = requests.post(
            url,
            auth=(sid, auth),
            data={
                "To": to_phone,
                "From": from_number,
                "Twiml": twiml
            },
            timeout=10
        )
        data = resp.json()
        if resp.status_code in (200, 201):
            return {"success": True, "call_sid": data.get("sid")}
        else:
            return {"success": False, "error": data.get("message", "Twilio error")}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# UNIFIED DISPATCHER
# Sends via all available channels based on severity
# ============================================================

def dispatch_alert(payload: NotificationPayload) -> dict:
    """
    Smart alert dispatcher:
    - INFO    → Telegram only
    - WARNING → Telegram + SMS
    - CRITICAL → Telegram + SMS + Voice Call
    """
    results = {}

    SEVERITY_EMOJIS = {
        "scheme":   "🏛️",
        "disaster": "🚨",
        "market":   "📈",
        "weather":  "🌦️"
    }
    emoji = SEVERITY_EMOJIS.get(payload.alert_type, "📢")

    # Format messages
    tg_message = (
        f"<b>{emoji} AgriSaathi Alert — {payload.title}</b>\n\n"
        f"{payload.message}\n\n"
        f"<i>Severity: {payload.severity} | AgriSaathi AI</i>"
    )

    # SMS truncation fix: only truncate and add '...' if OVER 160 characters
    raw_sms = f"[AgriSaathi] {emoji} {payload.title}\n{payload.message}"
    if len(raw_sms) > 160:
        sms_message = raw_sms[:157] + "..."
    else:
        sms_message = raw_sms

    call_message = (
        f"AgriSaathi AI Alert for {payload.farmer.name}. "
        f"{payload.title}. "
        f"{payload.message[:200]}"
    )

    # Telegram (all severities)
    if payload.farmer.telegram_chat_id:
        results["telegram"] = send_telegram_message(
            payload.farmer.telegram_chat_id,
            tg_message
        )

    # SMS (WARNING + CRITICAL)
    if payload.severity in ("WARNING", "CRITICAL"):
        results["sms"] = send_sms_alert(payload.farmer.phone, sms_message)

    # Voice Call (CRITICAL only — disasters, floods, etc.)
    if payload.severity == "CRITICAL":
        results["voice_call"] = send_voice_call_alert(payload.farmer.phone, call_message, lang=payload.farmer.lang)

    return {
        "dispatched": True,
        "severity": payload.severity,
        "channels_attempted": list(results.keys()),
        "results": results
    }
