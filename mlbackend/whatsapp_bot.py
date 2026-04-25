"""
AgriSaathi — WhatsApp Chatbot Webhook (Meta API)
================================================
Handles incoming Meta WhatsApp messages.
Routes based on message type (image, location, text).
Includes Language Auto-Detection and Feature Menu.
"""

import os
import requests
from fastapi import APIRouter, Request, BackgroundTasks, Query, HTTPException
from fastapi.responses import PlainTextResponse
from typing import Optional

from .services import translate_text, detect_language_from_coords
from .llm_service import get_llm_response
from .disease_classifier import disease_classifier
from .config import settings
from .supabase_client import log_message, get_chat_history, format_chat_history

router = APIRouter()

# Simple language detection cache (In production, use a database or user session)
USER_LANGUAGES = {}

def detect_text_language(text: str) -> str:
    """Uses LLM to detect the language code of the text."""
    prompt = f"Detect the language of this text. Reply with ONLY the 2-letter ISO 639-1 code (e.g. 'en', 'hi', 'mr', 'ta', 'te'). Text: '{text}'"
    lang_code = get_llm_response(prompt=prompt, system_prompt="You are a language detector.")
    return lang_code.strip().lower()

def send_whatsapp_reply(to_number: str, message: str, lang_code: str = "en"):
    """Sends a WhatsApp reply via Meta Graph API."""
    token = settings.META_WHATSAPP_TOKEN
    phone_id = settings.META_PHONE_NUMBER_ID
    
    # Translate message if needed
    if lang_code and lang_code != "en" and not message.startswith("System Error"):
        try:
            message = translate_text(message, lang_code)
        except:
            pass # fallback to English if translation fails

    if not token or not phone_id:
        print(f"Simulation Mode WhatsApp Reply to {to_number} (Lang: {lang_code}):\n{message}")
        return
        
    url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message}
    }
    
    try:
        requests.post(url, headers=headers, json=payload, timeout=10)
        # Log bot reply
        log_message(to_number, "bot", "text", message)
    except Exception as e:
        print(f"Meta WhatsApp Error: {e}")

def get_feature_menu() -> str:
    return """🌾 *AgriSaathi Features:*
1️⃣ *Disease Detection:* Send a clear photo of a diseased leaf.
2️⃣ *Crop & Weather Risk:* Send your location pin.
3️⃣ *Expert Advice:* Type any agriculture question.
4️⃣ *Chat History:* Type '4' to view your past messages.
How can I help you today?"""

def process_image(media_id: str, sender: str, lang_code: str):
    """Downloads image from Meta API and runs CNN inference."""
    log_message(sender, "user", "image", "Sent an image for disease detection.")
    token = settings.META_WHATSAPP_TOKEN
    
    if not token:
        # Simulation mode fallback
        send_whatsapp_reply(sender, "Simulation Mode: Cannot download image without Meta token.", lang_code)
        return
        
    try:
        # Step 1: Get Media URL from Media ID
        url_res = requests.get(
            f"https://graph.facebook.com/v17.0/{media_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        url_res.raise_for_status()
        media_url = url_res.json().get("url")
        
        # Step 2: Download the actual image bytes
        img_res = requests.get(
            media_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15
        )
        img_res.raise_for_status()
        image_bytes = img_res.content
        
        # Run CNN inference
        result = disease_classifier.classify_image(image_bytes)
        
        if "error" in result:
            reply = f"System Error: {result['error']}\n\nRunning in simulation mode? Make sure to train the model first."
        elif result["is_healthy"]:
            reply = f"🌿 *Diagnosis:* {result['display_name']}\n\nConfidence: {result['confidence_percent']}%\n\n✅ Great news! Your crop appears healthy. Maintain standard care."
        else:
            reply = f"🚨 *Disease Detected:* {result['display_name']}\n\nConfidence: {result['confidence_percent']}%\n\n💊 *Recommended Treatment:*\n{result['treatment']}"
            
        send_whatsapp_reply(sender, reply, lang_code)
        
    except Exception as e:
        send_whatsapp_reply(sender, f"Sorry, an error occurred while analyzing the image: {str(e)}", lang_code)

def process_text(text: str, sender: str, lang_code: str):
    """Processes natural language questions using LLM."""
    text_lower = text.strip().lower()
    
    # Log user message
    log_message(sender, "user", "text", text)
    
    # Handle Chat History request
    if text_lower == "4" or "history" in text_lower or "इतिहास" in text_lower:
        history = get_chat_history(sender, limit=10)
        reply = format_chat_history(history)
        send_whatsapp_reply(sender, reply, lang_code)
        return
        
    # If greeting or asking for help, send menu
    greetings = ['hi', 'hello', 'hey', 'help', 'menu', 'नमस्ते', 'hello agrisaathi']
    if any(g in text_lower for g in greetings) or len(text_lower) < 3:
        reply = "👋 Hello! I am AgriSaathi, your AI agricultural advisor.\n\n" + get_feature_menu()
        send_whatsapp_reply(sender, reply, lang_code)
        return

    sys_prompt = "You are AgriSaathi, an expert AI agricultural advisor. Give short, direct answers formatted for WhatsApp (use emojis, short paragraphs). Assume the farmer is in India. Provide your response in English; it will be translated later."
    prompt = f"Farmer asks: {text}"
    
    reply = get_llm_response(prompt=prompt, system_prompt=sys_prompt)
    send_whatsapp_reply(sender, reply, lang_code)

def process_location(lat: float, lon: float, sender: str, lang_code: str):
    """Processes a location pin."""
    log_message(sender, "user", "location", f"Sent location pin ({lat}, {lon})")
    from .main import crop_risk_intelligence, CropRiskRequest
    
    # 1. Update language based on location if not already established
    loc_lang_code, lang_name, state = detect_language_from_coords(lat, lon)
    if sender not in USER_LANGUAGES or USER_LANGUAGES[sender] == "en":
        USER_LANGUAGES[sender] = loc_lang_code
        lang_code = loc_lang_code
    
    # 2. Get risk intelligence
    try:
        req = CropRiskRequest(lat=lat, lon=lon, lang="en")
        risk_data = crop_risk_intelligence(req)
        
        reply = (
            f"📍 *Location Detected:* {state}\n"
            f"🗣️ *Language Auto-Updated:* {lang_name}\n\n"
            f"{risk_data['risk']['color']} *Crop Risk Level:* {risk_data['risk']['level']} ({risk_data['risk']['score']}/100)\n\n"
            f"🌦️ *Current Weather:* {risk_data['current_weather']['temp']}°C, {risk_data['current_weather']['description']}\n\n"
            f"🤖 *AI Advice:*\n{risk_data['ai_advice']}"
        )
    except Exception as e:
        reply = f"Received location: {lat}, {lon} in {state}. Could not fetch weather risk data: {e}"
        
    send_whatsapp_reply(sender, reply, lang_code)


@router.get("/api/whatsapp/webhook/")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """Meta Webhook Verification Endpoint."""
    verify_token = settings.META_WEBHOOK_VERIFY_TOKEN
    
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        print("Webhook verified successfully!")
        return PlainTextResponse(hub_challenge)
    
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/api/whatsapp/webhook/")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Main Meta WhatsApp Webhook endpoint."""
    try:
        body = await request.json()
    except:
        return {"status": "error", "message": "Invalid JSON"}

    # Validate that this is a WhatsApp API event
    if body.get("object") != "whatsapp_business_account":
        return {"status": "ignored"}
        
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])
            
            for msg in messages:
                sender = msg.get("from")
                msg_type = msg.get("type")
                
                # Language Detection Phase
                lang_code = USER_LANGUAGES.get(sender, "en")
                
                if msg_type == "text":
                    text = msg.get("text", {}).get("body", "")
                    
                    # Auto-detect language on first text message
                    if sender not in USER_LANGUAGES and text:
                        detected_lang = detect_text_language(text)
                        if len(detected_lang) == 2: # basic validation
                            USER_LANGUAGES[sender] = detected_lang
                            lang_code = detected_lang
                            
                    background_tasks.add_task(process_text, text, sender, lang_code)
                    
                elif msg_type == "image":
                    media_id = msg.get("image", {}).get("id")
                    background_tasks.add_task(process_image, media_id, sender, lang_code)
                    
                elif msg_type == "location":
                    lat = msg.get("location", {}).get("latitude")
                    lon = msg.get("location", {}).get("longitude")
                    background_tasks.add_task(process_location, lat, lon, sender, lang_code)
                    
                else:
                    send_whatsapp_reply(sender, f"Unsupported message type: {msg_type}. Please send text, an image, or a location.", lang_code)
                    
    return {"status": "success"}

@router.get("/api/whatsapp/status")
def whatsapp_status():
    return {
        "status": "Online",
        "webhook_url": "/api/whatsapp/webhook",
        "disease_model_loaded": disease_classifier.is_loaded,
        "platform": "Meta Cloud API"
    }
