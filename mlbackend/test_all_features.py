"""
AgriSaathi — Test All Core Features
===================================
A comprehensive script to test all 8 backend endpoints.
It does not require API keys (works in simulation mode).
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def print_result(feature_name: str, res: requests.Response):
    print(f"\n[{'✅ PASS' if res.status_code == 200 else '❌ FAIL'}] {feature_name}")
    if res.status_code != 200:
        print(f"Error: {res.text}")
    else:
        try:
            data = res.json()
            print(json.dumps(data, indent=2)[:500] + "...\n" if len(str(data)) > 500 else json.dumps(data, indent=2))
        except:
            print(f"(Binary Response: {len(res.content)} bytes)")

def run_tests():
    print("=" * 60)
    print("🌾 AgriSaathi — Core Features System Test")
    print("=" * 60)

    # 0. Health Check
    try:
        res = requests.get(f"{BASE_URL}/", timeout=2)
        print_result("0. API Health Check", res)
    except requests.exceptions.ConnectionError:
        print("\n❌ CRITICAL: Server is not running!")
        print("Please start it in another terminal using:")
        print("uvicorn mlbackend.main:app --reload")
        return

    # 1. Pest & Disease Rule Engine
    pest_payload = {
        "crop": "rice",
        "growth_stage": "vegetative",
        "temperature": 33.5,
        "humidity": 88.0,
        "symptoms_observed": "yellowing leaves",
        "lang": "en"
    }
    res = requests.post(f"{BASE_URL}/api/pest-disease", json=pest_payload)
    print_result("1. Pest & Disease Prediction Engine", res)

    # 2. Weather Risk
    risk_payload = {
        "lat": 28.6139,
        "lon": 77.2090,
        "crop": "wheat",
        "stage": "seedling",
        "lang": "en"
    }
    res = requests.post(f"{BASE_URL}/api/crop-risk", json=risk_payload)
    print_result("2. Weather-Based Crop Risk Intelligence", res)



    # 4. Text-to-Speech
    res = requests.get(f"{BASE_URL}/api/tts?text=Welcome to AgriSaathi&lang=en")
    print_result("4. Text-to-Speech (TTS)", res)

    # 5. Geolocation Language Detection
    loc_payload = {"lat": 19.0760, "lon": 72.8777} # Mumbai, Maharashtra -> should be Marathi
    res = requests.post(f"{BASE_URL}/api/detect-language", json=loc_payload)
    print_result("5. Geolocation Language Detection", res)

    # 6. Weather Map Data (Forecast)
    res = requests.post(f"{BASE_URL}/api/forecast", json=loc_payload)
    print_result("6. Climate & Weather Forecast", res)

    # 7. Crop Recommendation (ML)
    crop_payload = {
        "N": 90, "P": 42, "K": 43, 
        "temperature": 20.8, "humidity": 82.0, "ph": 6.5, "rainfall": 202.9,
        "lang": "en"
    }
    res = requests.post(f"{BASE_URL}/api/crop-recommend", json=crop_payload)
    print_result("7. Crop Recommendation (ML Model)", res)
    
    # 8. WhatsApp Webhook (Simulation)
    wa_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123456789",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "1234567890",
                        "phone_number_id": "1234567890"
                    },
                    "messages": [{
                        "from": "1234567890",
                        "id": "wamid.1234567890",
                        "timestamp": "1234567890",
                        "text": {"body": "Hello AgriSaathi, I have a pest problem in my rice field."},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    res = requests.post(f"{BASE_URL}/api/whatsapp/webhook", json=wa_payload)
    print_result("8. WhatsApp Webhook Chatbot (Meta API)", res)

if __name__ == "__main__":
    run_tests()
