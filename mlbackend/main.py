"""
AgriSaathi Core Features — Backend Server
==========================================
Contains only the 8 core features for PS08 (Crop Protection Advisory):
1. Pest & Disease Prediction Engine
6. Weather-Based Crop Risk Intelligence
4. Voice Detection — Twilio IVR
5. Text-to-Speech (TTS) Voice Alert Engine
6. Multilingual Text Translation
7. Geolocation-Based Language Detection
8. Live Climate & Weather Map
"""

import os
import sys
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

import requests

from .services import get_weather, get_forecast, get_soil_data, translate_text, detect_language_from_coords
from .llm_service import get_llm_response
from .config import settings

# Service Imports with fallbacks
try:
    from .pest_service import PestInput, analyze_pest_risk
except ImportError:
    class PestInput(BaseModel): lang: str = "en"
    def analyze_pest_risk(x): return {"error": "Module offline"}

app = FastAPI(title="AgriSaathi Core Features — PS08 Crop Protection Advisory")

# Optional: Include Twilio IVR router if available
try:
    from .twilio_ivr import router as ivr_router
    app.include_router(ivr_router)
    print("Twilio IVR features enabled")
except ImportError:
    print("Warning: Twilio not installed - IVR features disabled")

# Include WhatsApp Bot Router
try:
    from .whatsapp_bot import router as wa_router
    app.include_router(wa_router)
    print("WhatsApp Bot features enabled")
except ImportError:
    print("Warning: WhatsApp bot features disabled")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# LANGUAGE MAP
# ============================================================

LANG_NAMES = {
    "en": "English", "hi": "Hindi", "te": "Telugu", "ta": "Tamil",
    "mr": "Marathi", "pa": "Punjabi", "bn": "Bengali", "kn": "Kannada",
    "gu": "Gujarati", "ml": "Malayalam", "or": "Odia", "as": "Assamese",
    "ur": "Urdu", "sa": "Sanskrit", "ks": "Kashmiri", "ne": "Nepali",
    "sd": "Sindhi", "mai": "Maithili", "doi": "Dogri", "mni": "Manipuri",
    "kok": "Konkani", "bho": "Bhojpuri"
}


# ============================================================
# SCHEMAS
# ============================================================

class LocationInput(BaseModel):
    lat: float
    lon: float
    crop: str = "rice"
    lang: str = "en"

class GeoLangRequest(BaseModel):
    lat: float
    lon: float

class CropRiskRequest(BaseModel):
    lat: float
    lon: float
    crop: str = "Paddy"
    stage: str = "Vegetative"
    lang: str = "en"



class CropRecommendRequest(BaseModel):
    N: float
    P: float
    K: float
    temperature: float
    humidity: float
    ph: float
    rainfall: float
    lang: str = "en"


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def read_root():
    return {
        "status": "AgriSaathi Core Features — Online",
        "modules": [
            "pest-disease", "crop-risk",
            "ivr-voice", "tts-voice", "translate",
            "detect-language", "weather-forecast",
            "crop-recommend", "disease-detect", "whatsapp-bot"
        ]
    }


# ============================================================
# FEATURE 1: PEST & DISEASE PREDICTION ENGINE
# ============================================================

@app.post("/api/pest-disease")
def pest_disease_prediction(data: PestInput):
    """
    Hybrid Pest & Disease Prediction Engine.
    Combines rule-based threat library + AI symptom diagnosis.
    """
    result = analyze_pest_risk(data)

    if data.lang != "en":
        result["threats"] = [translate_text(t, data.lang) for t in result["threats"]]
        result["actions"] = [translate_text(a, data.lang) for a in result["actions"]]
        result["summary"] = translate_text(result["summary"], data.lang)
        if result.get("ai_diagnosis") and len(result["ai_diagnosis"]) < 10:
             result["ai_diagnosis"] = translate_text(result["ai_diagnosis"], data.lang)

    return result


@app.post("/api/disease-detect")
async def detect_leaf_disease(request: Request):
    """
    CNN Image Classification for Leaf Diseases.
    Accepts raw image bytes via POST body or multipart form.
    """
    from .disease_classifier import disease_classifier
    
    try:
        content_type = request.headers.get("content-type", "")
        if "multipart/form-data" in content_type:
            form = await request.form()
            image_file = form.get("image")
            if not image_file:
                raise HTTPException(status_code=400, detail="No image file provided")
            image_bytes = await image_file.read()
        else:
            image_bytes = await request.body()
            
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Empty request body")
            
        result = disease_classifier.classify_image(image_bytes)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/crop-recommend")
def recommend_crop(req: CropRecommendRequest):
    """
    ML Crop Recommendation based on NPK and Weather data.
    Uses trained RandomForest model.
    """
    import os
    import joblib
    import pandas as pd
    
    model_path = os.path.join(os.path.dirname(__file__), "crop_model.joblib")
    if not os.path.exists(model_path):
        return {"error": "Model not trained. Run train_crop_model.py first."}
        
    try:
        model = joblib.load(model_path)
        input_data = pd.DataFrame([{
            'N': req.N, 'P': req.P, 'K': req.K,
            'temperature': req.temperature, 'humidity': req.humidity,
            'ph': req.ph, 'rainfall': req.rainfall
        }])
        
        prediction = model.predict(input_data)[0]
        
        # Translate recommendation if needed
        recommendation = prediction.capitalize()
        if req.lang != "en":
            recommendation = translate_text(recommendation, req.lang)
            
        return {
            "recommended_crop": recommendation,
            "original_prediction": prediction,
            "inputs": input_data.to_dict(orient='records')[0]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

# ============================================================
# FEATURE 2: WEATHER-BASED CROP RISK INTELLIGENCE
# ============================================================

@app.post("/api/crop-risk")
@app.post("/api/weather-advice")  # Alias for backward compatibility
def crop_risk_intelligence(req: CropRiskRequest):
    """
    Predictive Crop Risk Engine.
    Combines current weather + 48h forecast to compute a Forward-Looking Risk Score.
    """
    weather = get_weather(req.lat, req.lon)
    forecast_data = get_forecast(req.lat, req.lon)

    if not weather:
        raise HTTPException(status_code=500, detail="Weather fetch failed.")

    temp = weather.get("temp", 25)
    rain = weather.get("rainfall_last_3h", 0)
    humidity = weather.get("humidity", 50)
    wind = weather.get("wind_speed", 5)

    # 1. Base Current Risk
    risk_now = max(0, (temp - 35) * 4) + min(30, rain * 1.5) + max(0, (humidity - 80) * 1.0)

    # 2. Predictive Forecast Risk (checking 48h for spikes)
    forecast_risk = 0
    max_forecast_temp = temp
    max_rain_prob = 0
    upcoming_threats = []

    if "forecast" in forecast_data:
        for entry in forecast_data["forecast"]:
            f_temp = entry["temp"]
            f_prob = entry["rain_prob"]
            if f_temp > 38:
                forecast_risk += 10
                upcoming_threats.append(f"Upcoming Heatwave ({f_temp}°C)")
            if f_temp < 10:
                forecast_risk += 15
                upcoming_threats.append(f"Frost Risk Detected ({f_temp}°C)")
            if f_prob > 70:
                forecast_risk += 20
                upcoming_threats.append(f"High Precipitation Certainty ({f_prob}%)")
            max_forecast_temp = max(max_forecast_temp, f_temp)
            max_rain_prob = max(max_rain_prob, f_prob)

    total_score = min(100, int(risk_now + (forecast_risk / 2) + (wind * 0.5)))

    # Risk classification
    if total_score < 25: level, color = "SAFE", "🟢"
    elif total_score < 55: level, color = "MODERATE", "🟡"
    elif total_score < 75: level, color = "HIGH", "🟠"
    else: level, color = "SEVERE", "🔴"

    # 3. Decision Support Analysis
    lang_name = LANG_NAMES.get(req.lang, "English")
    sys_prompt = f"You are AgriSaathi's Precision Predictive AI. Respond in {lang_name}."
    prompt = (
        f"DATA REPORT:\n- CURRENT: {temp}°C, {rain}mm rain, {humidity}% humidity.\n"
        f"- FORECAST: Max {max_forecast_temp}°C, Max Rain Prob {max_rain_prob}%.\n"
        f"- THREATS: {', '.join(upcoming_threats) if upcoming_threats else 'None'}.\n"
        f"- CROP: {req.crop} ({req.stage} stage).\n"
        f"- OVERALL RISK: {total_score}/100 ({level}).\n\n"
        f"Help the farmer prepare in {lang_name}:\n"
        f"1. EXPLANATION: Why is this risk level assigned? (3-4 sentences)\n"
        f"2. PREVENTATIVE ACTIONS: 5 detailed things to do NOW to save the crop from the upcoming conditions.\n"
        f"3. HARVEST IMPACT: How will this affect yield?"
    )
    res_text = get_llm_response(prompt=prompt, system_prompt=sys_prompt)

    return {
        "location": {"lat": req.lat, "lon": req.lon},
        "crop": req.crop,
        "stage": req.stage,
        "risk": {
            "score": total_score,
            "level": level,
            "color": color,
            "threats_detected": upcoming_threats
        },
        "ai_advice": res_text,
        "current_weather": weather,
        "forecast_summary": f"Next 48h: Max {max_forecast_temp}°C, Rain potential up to {max_rain_prob}%",
        "timestamp": datetime.now().strftime("%I:%M %p, %d %b")
    }


@app.post("/api/forecast")
def get_extended_forecast(req: GeoLangRequest):
    """Fetches high-precision 5-day / 3-hour agricultural forecast."""
    return get_forecast(req.lat, req.lon)





# ============================================================
# FEATURE 5: TEXT-TO-SPEECH (TTS) VOICE ALERT ENGINE
# ============================================================

@app.get("/api/tts")
def generate_voice_alert(text: str = Query(..., description="Text to speak"), lang: str = Query("hi", description="Language code")):
    """
    Converts text alerts into audible MP3 files using Google TTS.
    Supports 11 Indian languages.
    """
    from gtts import gTTS
    import io

    tts_lang = lang.lower()
    supported_gtts = ["en", "hi", "te", "ta", "mr", "pa", "bn", "gu", "ml", "ne", "ur"]

    if tts_lang not in supported_gtts:
        tts_lang = "hi"

    try:
        tts = gTTS(text=text, lang=tts_lang)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return Response(content=fp.read(), media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS Generation failed: {e}")


# ============================================================
# FEATURE 7: GEOLOCATION-BASED LANGUAGE DETECTION
# ============================================================

@app.post("/api/detect-language")
def detect_language(req: GeoLangRequest):
    """Detects the best regional language based on GPS coordinates."""
    lang_code, lang_name, state_name = detect_language_from_coords(req.lat, req.lon)
    return {
        "detected_language_code": lang_code,
        "detected_language_name": lang_name,
        "detected_state": state_name,
        "lat": req.lat,
        "lon": req.lon
    }


# ============================================================
# STARTUP
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("AgriSaathi Core Features — Backend Server")
    print("=" * 60)
    print("Starting server on http://127.0.0.1:8000")
    print("=" * 60)

    try:
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    except KeyboardInterrupt:
        print("\nServer stopped")
    except Exception as e:
        print(f"Error: {e}")
