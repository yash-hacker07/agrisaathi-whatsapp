"""
AgriSaathi — Disease Classification Inference Module
======================================================
Loads the trained MobileNetV2 model and performs inference on images.
Optimized for accepting raw image bytes from WhatsApp webhooks.
"""

import os
import json
import numpy as np
from io import BytesIO

# Suppress TF warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

class DiseaseClassifier:
    def __init__(self):
        self.model = None
        self.class_labels = {}
        self.is_loaded = False
        
        self.model_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_path = os.path.join(self.model_dir, "disease_model.h5")
        self.labels_path = os.path.join(self.model_dir, "class_labels.json")
        
        # Treatment mapping (simplified subset for demonstration)
        self.treatments = {
            "Apple___Apple_scab": "Apply Captan or Mancozeb fungicide. Rake and destroy fallen leaves.",
            "Apple___Black_rot": "Prune out dead or diseased branches. Apply Captan fungicide.",
            "Apple___Cedar_apple_rust": "Remove cedar galls from nearby junipers. Apply Myclobutanil.",
            "Apple___healthy": "Crop is healthy. Maintain standard care.",
            "Cherry_(including_sour)___Powdery_mildew": "Apply sulfur or myclobutanil based fungicides.",
            "Cherry_(including_sour)___healthy": "Crop is healthy. Maintain standard care.",
            "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "Apply Azoxystrobin or Pyraclostrobin. Practice crop rotation.",
            "Corn_(maize)___Common_rust_": "Apply Pyraclostrobin or Propiconazole if severe.",
            "Corn_(maize)___Northern_Leaf_Blight": "Apply Maneb or Mancozeb. Plant resistant hybrids.",
            "Corn_(maize)___healthy": "Crop is healthy. Maintain standard care.",
            "Grape___Black_rot": "Apply Mancozeb or Captan. Remove mummified berries.",
            "Grape___Esca_(Black_Measles)": "Prune out infected wood. No effective chemical control, prevention is key.",
            "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": "Apply Bordeaux mixture or copper-based fungicides.",
            "Grape___healthy": "Crop is healthy. Maintain standard care.",
            "Orange___Haunglongbing_(Citrus_greening)": "No cure. Remove infected trees to prevent spread. Control psyllids.",
            "Peach___Bacterial_spot": "Apply copper-based bactericides in early spring.",
            "Peach___healthy": "Crop is healthy. Maintain standard care.",
            "Pepper,_bell___Bacterial_spot": "Apply copper-based sprays. Rotate crops.",
            "Pepper,_bell___healthy": "Crop is healthy. Maintain standard care.",
            "Potato___Early_blight": "Apply Chlorothalonil or Mancozeb. Rotate crops.",
            "Potato___Late_blight": "Apply Chlorothalonil or copper fungicides. Destroy infected vines.",
            "Potato___healthy": "Crop is healthy. Maintain standard care.",
            "Squash___Powdery_mildew": "Apply Neem oil or sulfur-based fungicides.",
            "Strawberry___Leaf_scorch": "Remove infected leaves. Apply copper fungicides.",
            "Strawberry___healthy": "Crop is healthy. Maintain standard care.",
            "Tomato___Bacterial_spot": "Apply copper fungicides. Avoid overhead watering.",
            "Tomato___Early_blight": "Apply Chlorothalonil or Mancozeb. Remove lower infected leaves.",
            "Tomato___Late_blight": "Apply Chlorothalonil. Remove and destroy infected plants.",
            "Tomato___Leaf_Mold": "Improve ventilation. Apply Chlorothalonil.",
            "Tomato___Septoria_leaf_spot": "Apply Chlorothalonil. Avoid overhead watering.",
            "Tomato___Spider_mites Two-spotted_spider_mite": "Apply insecticidal soap or Neem oil. Introduce predatory mites.",
            "Tomato___Target_Spot": "Apply Chlorothalonil or Azoxystrobin. Improve airflow.",
            "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Control whiteflies. Remove infected plants.",
            "Tomato___Tomato_mosaic_virus": "No cure. Remove infected plants. Disinfect tools.",
            "Tomato___healthy": "Crop is healthy. Maintain standard care."
        }

    def load_model(self):
        """Loads the TF model and labels into memory."""
        if self.is_loaded:
            return True
            
        if not os.path.exists(self.model_path) or not os.path.exists(self.labels_path):
            print("⚠️ Disease model not found. Run train_disease_model.py first.")
            return False
            
        try:
            # Lazy import tensorflow only when needed to save memory
            from tensorflow.keras.models import load_model as keras_load_model
            self.model = keras_load_model(self.model_path)
            
            with open(self.labels_path, 'r') as f:
                labels_dict = json.load(f)
                # Ensure keys are integers since json saves keys as strings
                self.class_labels = {int(k): v for k, v in labels_dict.items()}
                
            self.is_loaded = True
            print("✅ Disease Classifier model loaded successfully.")
            return True
        except Exception as e:
            print(f"❌ Error loading disease model: {e}")
            return False

    def classify_image(self, image_bytes: bytes) -> dict:
        """
        Classifies a raw image bytes array.
        Returns diagnosis dict with class name, confidence, and treatment.
        """
        if not self.load_model():
            return {"error": "Model not trained. Cannot classify."}
            
        try:
            from PIL import Image
            from tensorflow.keras.preprocessing.image import img_to_array
            
            # Load and preprocess image
            img = Image.open(BytesIO(image_bytes))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img = img.resize((224, 224))
            
            x = img_to_array(img)
            x = np.expand_dims(x, axis=0)
            x = x / 255.0  # Normalize to [0,1]
            
            # Inference
            preds = self.model.predict(x, verbose=0)[0]
            class_idx = int(np.argmax(preds))
            confidence = float(preds[class_idx])
            
            class_name = self.class_labels.get(class_idx, "Unknown")
            
            # Clean up class name for display
            display_name = class_name.replace("___", " - ").replace("_", " ")
            
            # Get treatment
            treatment = self.treatments.get(class_name, "Consult local agricultural expert for specific treatment.")
            
            is_healthy = "healthy" in class_name.lower()
            
            return {
                "success": True,
                "disease_id": class_name,
                "display_name": display_name,
                "confidence": confidence,
                "confidence_percent": round(confidence * 100, 1),
                "is_healthy": is_healthy,
                "treatment": treatment
            }
            
        except Exception as e:
            return {"error": f"Inference failed: {str(e)}"}

# Global instance for FastAPI
disease_classifier = DiseaseClassifier()
