# 🌾 AgriSaathi — Feature Description Document

**Problem Statement:** PS08 — Agriculture (Crop Protection Advisory System)  
**Category:** Agriculture  
**Platform:** AI-Powered Crop Protection & Agricultural Governance Copilot  

---

## 📌 Problem Statement Overview

Crop loss can happen due to many reasons including insect infestation, bird damage, animal intrusion, weather stress, and changing environmental conditions. Farmers often rely on scattered advice or traditional knowledge, which may not always match the current crop stage, local context, or severity of the problem. AgriSaathi solves this by providing an intelligent, AI-driven crop protection advisory system that delivers timely, crop-specific, and condition-based guidance to farmers in their own regional language.

---

## 🧠 Core Features

---

### 1. 🐛 Pest & Disease Prediction Engine

**Endpoint:** `POST /api/pest-disease`  
**Backend File:** `mlbackend/pest_service.py`

AgriSaathi features a hybrid pest and disease prediction engine that combines a deterministic rule-based threat library with AI-powered symptom diagnosis. The system maintains a curated pest library covering major Indian crops — Rice, Wheat, Cotton, Maize, and Tomato — with known threat triggers based on humidity, temperature, and growth stage conditions.

**How It Works:**
- The farmer provides their crop type, growth stage (Sowing, Seedling, Vegetative, Flowering, Fruiting), current temperature, humidity, recent rainfall, and optionally describes any observed symptoms (e.g., "yellowing leaves", "holes in leaves").
- The rule-based engine immediately checks for known threats. For example, if a rice farmer reports humidity above 85%, the system flags **Rice Blast (Magnaporthe oryzae)** and recommends applying Tricyclazole 75WP at 0.6g/L.
- If the farmer has described symptoms, the AI layer (powered by Groq/Gemini LLM) acts as a professional plant pathologist to diagnose the probable cause, recommend immediate treatment (chemical and organic options), and issue red-list warnings if the disease is contagious.
- A composite risk score (0–100) is calculated and classified as LOW, MEDIUM, HIGH, or CRITICAL.
- All outputs are automatically translated into the farmer's regional language.

**Key Threats Covered:**
| Crop | Threat | Trigger Condition |
|------|--------|-------------------|
| Rice | Rice Blast, Brown Plant Hopper, Stem Borer | Humidity > 85%, Temp > 32°C, Vegetative stage |
| Wheat | Yellow Rust, Aphid Colony | Humidity > 80%, Flowering stage |
| Cotton | Bollworm, Red Spider Mite | Vegetative/Flowering, Temp > 35°C |
| Maize | Fall Armyworm, Downy Mildew | Seedling stage, Humidity > 80% |
| Tomato | Early Blight, Fruit Borer | Humidity > 75%, Flowering/Fruiting |

---

### 2. 🌤️ Weather-Based Crop Risk Intelligence

**Endpoint:** `POST /api/crop-risk`  
**Backend File:** `mlbackend/main.py` (Module 3)

This is a predictive crop risk engine that goes beyond reporting current weather. It combines real-time weather data with a 48-hour forecast to compute a **Forward-Looking Risk Score**, enabling farmers to take preventative action BEFORE adverse weather hits.

**How It Works:**
- The system fetches live weather data (temperature, humidity, rainfall, wind speed) from the OpenWeather API for the farmer's GPS coordinates.
- It then analyses the 48-hour forecast for upcoming threats — heatwaves (>38°C), frost risk (<10°C), and high precipitation certainty (>70%).
- A combined risk score is calculated from current conditions, forecast risk, and wind factor, then classified as:
  - 🟢 **SAFE** (score < 25)
  - 🟡 **MODERATE** (25–54)
  - 🟠 **HIGH** (55–74)
  - 🔴 **SEVERE** (75–100)
- The AI advisor then generates a detailed response in the farmer's language containing: an explanation of why this risk level was assigned, 5 detailed preventative actions to take immediately, and a harvest impact analysis.

---

### 3. 🛰️ Satellite Crop Monitoring (Remote Sensing)

**Endpoint:** `POST /api/satellite-analysis`  
**Backend Files:** `mlbackend/satellite_service.py`, `mlbackend/main.py` (Module 11)

AgriSaathi integrates with the ESA Copernicus Sentinel-2 satellite system to provide remote sensing crop health analysis. This feature allows farmers and agricultural officers to monitor field health without physically visiting the site.

**How It Works:**
- The system queries Sentinel-2 L2A satellite imagery for a defined bounding box around the farmer's field coordinates.
- An evalscript runs on Sentinel Hub servers to calculate vegetation indices directly from spectral bands (B02, B04, B08):
  - **NDVI** (Normalized Difference Vegetation Index) — measures overall vegetation health
  - **EVI** (Enhanced Vegetation Index) — improves sensitivity in high-biomass regions
  - **SAVI** (Soil Adjusted Vegetation Index) — accounts for soil brightness
- The system generates a health score (EXCELLENT / GOOD / MODERATE / STRESSED), a 14-day NDVI trend chart, and anomaly detection (low biomass zones, waterlogging, boundary stress).
- An AI analyst interprets the satellite data and provides actionable field management recommendations.
- If Sentinel Hub API keys are not configured, the system gracefully falls back to simulated data with a clear warning.

---

### 4. 🎙️ Voice Detection — Twilio IVR (Interactive Voice Response)

**Endpoint:** `POST /api/ivr/incoming`, `POST /api/ivr/process`  
**Backend File:** `mlbackend/twilio_ivr.py`

One of AgriSaathi's most inclusive features is its phone-based voice Q&A system. Many Indian farmers have limited literacy or may not have smartphones, so this feature allows them to call a phone number and speak their farming question in Hindi.

**How It Works:**
- When a farmer dials the AgriSaathi phone number, Twilio routes the call to `/api/ivr/incoming`.
- The system greets the farmer and uses Twilio's `Gather` function with `input='speech'` to capture the farmer's spoken question. The language is set to `hi-IN` (Hindi-India) by default.
- Twilio's built-in speech recognition transcribes the spoken audio to text and sends it to `/api/ivr/process`.
- The transcribed question is then sent to the LLM (Groq/Gemini) with a system prompt optimized for concise, phone-friendly agricultural answers.
- The AI-generated response is spoken back to the farmer over the phone using Twilio's text-to-speech, and the call is then ended.

**Key Design Decisions:**
- Default language is Hindi (`hi-IN`) since the majority of Indian farmers speak Hindi.
- Answers are kept concise and direct, suitable for reading aloud over a phone call.
- A 5-second timeout is set for speech capture, with a fallback message if no input is received.

---

### 5. 🔊 Text-to-Speech (TTS) Voice Alert Engine

**Endpoint:** `GET /api/tts?text=...&lang=hi`  
**Backend File:** `mlbackend/main.py` (Module 13)

This feature converts any text alert (such as weather warnings, pest alerts, or scheme notifications) into audible MP3 audio files using Google's Text-to-Speech engine (gTTS).

**How It Works:**
- The API accepts a `text` parameter and a `lang` parameter (default: Hindi).
- It validates the language against a list of 11 supported Indian languages: English, Hindi, Telugu, Tamil, Marathi, Punjabi, Bengali, Gujarati, Malayalam, Nepali, and Urdu.
- If the requested language is not supported by gTTS, it falls back to Hindi.
- The generated audio is returned as a streaming `audio/mpeg` response that can be played directly in the browser or over a phone call.

**Use Cases:**
- Reading out weather warnings to farmers who cannot read.
- Playing pest alert notifications in regional languages.
- Making government scheme information accessible via audio.

---

### 6. 🌐 Multilingual Text Translation

**Backend File:** `mlbackend/services.py`  
**Function:** `translate_text(text, target_lang)`

AgriSaathi supports 22+ Indian languages through its translation engine, ensuring that every piece of advice — from pest warnings to fertilizer schedules — is delivered in the farmer's mother tongue.

**How It Works:**
- Uses the `deep-translator` library (Google Translate backend) for accurate multilingual translation.
- Long texts are automatically chunked into ≤4,500 character segments at sentence boundaries to stay within API limits.
- Each chunk is translated independently and reassembled.
- A retry mechanism (2 attempts) handles transient API failures, with graceful fallback to the original text if translation fails.
- Translation is applied across ALL modules: pest threats, fertilizer recommendations, soil health insights, yield predictions, crop rotation plans, market price information, and scheme details.

**Supported Languages:**

| Code | Language | Code | Language |
|------|----------|------|----------|
| hi | Hindi | bn | Bengali |
| te | Telugu | kn | Kannada |
| ta | Tamil | gu | Gujarati |
| mr | Marathi | ml | Malayalam |
| pa | Punjabi | or | Odia |
| as | Assamese | ur | Urdu |
| sa | Sanskrit | ks | Kashmiri |
| ne | Nepali | sd | Sindhi |
| mai | Maithili | doi | Dogri |
| mni | Manipuri | kok | Konkani |
| bho | Bhojpuri | — | — |

---

### 7. 📍 Geolocation-Based Language Detection

**Endpoint:** `POST /api/detect-language`  
**Backend File:** `mlbackend/services.py`  
**Function:** `detect_language_from_coords(lat, lon)`

This feature automatically detects the farmer's preferred regional language based on their GPS coordinates, eliminating the need for manual language selection.

**How It Works:**
- The farmer's latitude and longitude are sent to the OpenStreetMap Nominatim reverse geocoding API (no API key required).
- The API returns the Indian state name for those coordinates.
- A curated `STATE_LANG_MAP` maps 20+ Indian states and union territories to their dominant regional language:
  - Uttar Pradesh, Bihar, Rajasthan, MP, etc. → Hindi
  - Maharashtra, Goa → Marathi
  - Tamil Nadu → Tamil
  - Karnataka → Kannada
  - West Bengal → Bengali
  - Punjab → Punjabi
  - And more...
- If the state is not found or the API fails, the system defaults to Hindi as a safe fallback.

---

### 8. 🗺️ Live Climate & Weather Map

**Endpoints:** `POST /api/crop-risk`, `POST /api/forecast`, `GET /api/weather` (via chat)  
**Backend File:** `mlbackend/services.py`  
**Frontend Route:** `src/app/climate-map/`

AgriSaathi provides real-time climate data and an interactive climate map for farmers to monitor weather conditions in their area.

**Backend Weather Features:**

**a) Real-Time Weather (`get_weather`)**
- Fetches current conditions from OpenWeather API for any GPS coordinates.
- Returns: temperature (°C), humidity (%), rainfall (last 3h in mm), wind speed (m/s), visibility (m), weather description, and location name.
- If the API key is not configured, returns simulated data with a clear "Simulation Mode" label.

**b) 5-Day / 3-Hour Forecast (`get_forecast`)**
- Provides 16 forecast data points across the next 48 hours at 3-hour intervals.
- Each data point includes: timestamp, temperature, weather condition, and rain probability (0–100%).
- This data feeds into the crop risk intelligence engine for proactive frost and flood alerts.

**c) Climate Map (Frontend)**
- A dedicated frontend page (`/climate-map`) visualizes live weather data on an interactive map, allowing farmers and agricultural officers to see climate conditions across regions.

---

## ⚙️ Technology Stack (Backend)

| Component | Technology |
|-----------|------------|
| Web Framework | FastAPI (Python) |
| ML Model | scikit-learn (RandomForest), joblib |
| AI/LLM | Groq (Llama) / Google Gemini |
| Weather Data | OpenWeather API |
| Satellite Data | ESA Sentinel-2 via Sentinel Hub |
| Soil Data | ISRIC SoilGrids v2 |
| Translation | deep-translator (Google Translate) |
| Voice (IVR) | Twilio (Speech-to-Text + TTS) |
| Voice (TTS) | gTTS (Google Text-to-Speech) |
| Database | Supabase (PostgreSQL) |
| Notifications | Telegram Bot API + Twilio SMS/Voice |
| Market Data | Data.gov.in (Agmarknet) |

---

## 📋 PS08 Requirements Compliance

| Requirement | Feature(s) | Status |
|---|---|---|
| Identify major threats to crops | Pest Library, Weather Risk Engine, Satellite Anomaly Detection | ✅ Fully Implemented |
| Provide practical prevention and protection suggestions | AI-generated treatment plans with exact dosages and actions | ✅ Fully Implemented |
| Support crop-specific and condition-based guidance | Pest Library keyed by crop + humidity/temp/stage triggers | ✅ Fully Implemented |
| Help reduce avoidable crop loss | 48h predictive risk scoring + automated CRON alerts + multi-channel notifications | ✅ Fully Implemented |
| Usability, clarity, and practical value | Multilingual support (22+ languages), voice access (IVR), TTS audio alerts | ✅ Fully Implemented |
| Empower farmers with understandable recommendations | Regional language translation, phone-based voice Q&A, simple risk scores | ✅ Fully Implemented |
