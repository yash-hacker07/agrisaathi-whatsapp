"""
AgriSaathi — WhatsApp Chatbot Webhook (Meta API)
================================================
Handles incoming Meta WhatsApp messages.
Routes based on message type (image, location, text).
Includes Language Auto-Detection and Feature Menu.
"""

import os
import logging
import requests
from fastapi import APIRouter, Request, BackgroundTasks, Query, HTTPException
from fastapi.responses import PlainTextResponse
from typing import Optional

logger = logging.getLogger(__name__)

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

    if not token and not phone_id:
        logger.warning("send_whatsapp_reply: META_WHATSAPP_TOKEN and META_PHONE_NUMBER_ID are both missing — running in simulation mode")
        logger.info("Simulation reply to %s (lang=%s): %s", to_number, lang_code, message)
        return

    if not token:
        logger.warning("send_whatsapp_reply: META_WHATSAPP_TOKEN is missing — cannot send reply to %s", to_number)
        return

    if not phone_id:
        logger.warning("send_whatsapp_reply: META_PHONE_NUMBER_ID is missing — cannot send reply to %s", to_number)
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

    logger.info("send_whatsapp_reply: POST %s | to=%s | lang=%s | body_length=%d", url, to_number, lang_code, len(message))

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        logger.info("send_whatsapp_reply: response status=%d | to=%s", response.status_code, to_number)
        if not response.ok:
            logger.error("send_whatsapp_reply: API error | status=%d | body=%s", response.status_code, response.text)
        else:
            logger.info("send_whatsapp_reply: reply sent successfully to %s", to_number)
            # Log bot reply
            log_message(to_number, "bot", "text", message)
    except Exception as e:
        logger.exception("send_whatsapp_reply: exception while sending reply to %s: %s", to_number, e)

def get_feature_menu() -> str:
    return """🌾 *AgriSaathi Features:*
1️⃣ *Disease Detection:* Send a clear photo of a diseased leaf.
2️⃣ *Crop & Weather Risk:* Send your location pin.
3️⃣ *Expert Advice:* Type any agriculture question.
4️⃣ *Chat History:* Type '4' to view your past messages.
How can I help you today?"""

def process_image(media_id: str, sender: str, lang_code: str):
    """Downloads image from Meta API and runs CNN inference."""
    logger.info("process_image: called | sender=%s | media_id=%s | lang=%s", sender, media_id, lang_code)
    log_message(sender, "user", "image", "Sent an image for disease detection.")
    token = settings.META_WHATSAPP_TOKEN
    
    if not token:
        # Simulation mode fallback
        send_whatsapp_reply(sender, "Simulation Mode: Cannot download image without Meta token.", lang_code)
        return
        
    try:
        # Step 1: Get Media URL from Media ID
        logger.info("process_image: fetching media URL for media_id=%s", media_id)
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
        logger.info("process_image: running CNN inference for sender=%s | image_size=%d bytes", sender, len(image_bytes))
        result = disease_classifier.classify_image(image_bytes)
        
        if "error" in result:
            reply = f"System Error: {result['error']}\n\nRunning in simulation mode? Make sure to train the model first."
        elif result["is_healthy"]:
            reply = f"🌿 *Diagnosis:* {result['display_name']}\n\nConfidence: {result['confidence_percent']}%\n\n✅ Great news! Your crop appears healthy. Maintain standard care."
        else:
            reply = f"🚨 *Disease Detected:* {result['display_name']}\n\nConfidence: {result['confidence_percent']}%\n\n💊 *Recommended Treatment:*\n{result['treatment']}"
            
        send_whatsapp_reply(sender, reply, lang_code)
        
    except Exception as e:
        logger.exception("process_image: exception for sender=%s: %s", sender, e)
        send_whatsapp_reply(sender, f"Sorry, an error occurred while analyzing the image: {str(e)}", lang_code)

def process_text(text: str, sender: str, lang_code: str):
    """Processes natural language questions using LLM."""
    logger.info("process_text: called | sender=%s | lang=%s | text_preview=%s", sender, lang_code, text[:80])
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
    
    logger.info("process_text: calling LLM for sender=%s", sender)
    reply = get_llm_response(prompt=prompt, system_prompt=sys_prompt)
    logger.info("process_text: LLM reply received for sender=%s | reply_length=%d", sender, len(reply))
    send_whatsapp_reply(sender, reply, lang_code)

def process_location(lat: float, lon: float, sender: str, lang_code: str):
    """Processes a location pin."""
    logger.info("process_location: called | sender=%s | lat=%s | lon=%s | lang=%s", sender, lat, lon, lang_code)
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
        logger.exception("process_location: exception fetching risk data for sender=%s: %s", sender, e)
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


def _run_process_text(text: str, sender: str, lang_code: str):
    """Wrapper around process_text with top-level exception logging."""
    logger.info("bg_task:process_text: starting | sender=%s | lang=%s | text_preview=%s", sender, lang_code, text[:80])
    try:
        process_text(text, sender, lang_code)
        logger.info("bg_task:process_text: completed | sender=%s", sender)
    except Exception as exc:
        logger.exception("bg_task:process_text: unhandled exception | sender=%s | error=%s", sender, exc)

def _run_process_image(media_id: str, sender: str, lang_code: str):
    """Wrapper around process_image with top-level exception logging."""
    logger.info("bg_task:process_image: starting | sender=%s | media_id=%s | lang=%s", sender, media_id, lang_code)
    try:
        process_image(media_id, sender, lang_code)
        logger.info("bg_task:process_image: completed | sender=%s", sender)
    except Exception as exc:
        logger.exception("bg_task:process_image: unhandled exception | sender=%s | error=%s", sender, exc)

def _run_process_location(lat: float, lon: float, sender: str, lang_code: str):
    """Wrapper around process_location with top-level exception logging."""
    logger.info("bg_task:process_location: starting | sender=%s | lat=%s | lon=%s | lang=%s", sender, lat, lon, lang_code)
    try:
        process_location(lat, lon, sender, lang_code)
        logger.info("bg_task:process_location: completed | sender=%s", sender)
    except Exception as exc:
        logger.exception("bg_task:process_location: unhandled exception | sender=%s | error=%s", sender, exc)


@router.post("/api/whatsapp/webhook/")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Main Meta WhatsApp Webhook endpoint."""
    logger.info("whatsapp_webhook: received POST request")

    try:
        body = await request.json()
    except Exception as exc:
        logger.error("whatsapp_webhook: failed to parse JSON body | error=%s", exc)
        return {"status": "error", "message": "Invalid JSON"}

    logger.info(
        "whatsapp_webhook: payload parsed | object=%s | entry_count=%d",
        body.get("object"),
        len(body.get("entry", [])),
    )

    # Validate that this is a WhatsApp API event
    if body.get("object") != "whatsapp_business_account":
        logger.warning("whatsapp_webhook: unexpected object type=%s — ignoring", body.get("object"))
        return {"status": "ignored"}

    for entry_idx, entry in enumerate(body.get("entry", [])):
        for change_idx, change in enumerate(entry.get("changes", [])):
            value = change.get("value", {})
            messages = value.get("messages", [])

            logger.info(
                "whatsapp_webhook: entry[%d] change[%d] | message_count=%d",
                entry_idx, change_idx, len(messages),
            )

            for msg_idx, msg in enumerate(messages):
                sender = msg.get("from")
                msg_type = msg.get("type")

                logger.info(
                    "whatsapp_webhook: message[%d] | sender=%s | type=%s",
                    msg_idx, sender, msg_type,
                )

                # Language Detection Phase
                lang_code = USER_LANGUAGES.get(sender, "en")

                if msg_type == "text":
                    text = msg.get("text", {}).get("body", "")

                    # Auto-detect language on first text message
                    if sender not in USER_LANGUAGES and text:
                        detected_lang = detect_text_language(text)
                        if len(detected_lang) == 2:  # basic validation
                            USER_LANGUAGES[sender] = detected_lang
                            lang_code = detected_lang
                            logger.info("whatsapp_webhook: language detected | sender=%s | lang=%s", sender, lang_code)

                    logger.info("whatsapp_webhook: queuing process_text task | sender=%s | lang=%s", sender, lang_code)
                    try:
                        background_tasks.add_task(_run_process_text, text, sender, lang_code)
                        logger.info("whatsapp_webhook: process_text task queued | sender=%s", sender)
                    except Exception as exc:
                        logger.exception("whatsapp_webhook: failed to queue process_text task | sender=%s | error=%s", sender, exc)

                elif msg_type == "image":
                    media_id = msg.get("image", {}).get("id")
                    logger.info("whatsapp_webhook: queuing process_image task | sender=%s | media_id=%s", sender, media_id)
                    try:
                        background_tasks.add_task(_run_process_image, media_id, sender, lang_code)
                        logger.info("whatsapp_webhook: process_image task queued | sender=%s", sender)
                    except Exception as exc:
                        logger.exception("whatsapp_webhook: failed to queue process_image task | sender=%s | error=%s", sender, exc)

                elif msg_type == "location":
                    lat = msg.get("location", {}).get("latitude")
                    lon = msg.get("location", {}).get("longitude")
                    logger.info("whatsapp_webhook: queuing process_location task | sender=%s | lat=%s | lon=%s", sender, lat, lon)
                    try:
                        background_tasks.add_task(_run_process_location, lat, lon, sender, lang_code)
                        logger.info("whatsapp_webhook: process_location task queued | sender=%s", sender)
                    except Exception as exc:
                        logger.exception("whatsapp_webhook: failed to queue process_location task | sender=%s | error=%s", sender, exc)

                else:
                    logger.warning("whatsapp_webhook: unsupported message type=%s | sender=%s", msg_type, sender)
                    send_whatsapp_reply(sender, f"Unsupported message type: {msg_type}. Please send text, an image, or a location.", lang_code)

    logger.info("whatsapp_webhook: returning success")
    return {"status": "success"}


@router.get("/api/whatsapp/status")
def whatsapp_status():
    return {
        "status": "Online",
        "webhook_url": "/api/whatsapp/webhook",
        "disease_model_loaded": disease_classifier.is_loaded,
        "platform": "Meta Cloud API"
    }
