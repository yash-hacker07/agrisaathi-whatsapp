"""
AgriSaathi — Crop Recommendation Model Training
===============================================
Trains a RandomForest model on soil and weather data to recommend the best crop.
Dataset: atharvaingle/crop-recommendation-dataset (Kaggle)

Usage:
  python -m mlbackend.train_crop_model
"""

import os
import sys
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib

def find_dataset():
    """Locates the crop recommendation CSV file."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(base, "datasets", "crop-recommendation", "Crop_recommendation.csv"),
        os.path.join(base, "datasets", "crop-recommendation", "crop_recommendation.csv"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def train():
    print("=" * 60)
    print("🌾 AgriSaathi — Crop Recommendation Model Training")
    print("=" * 60)

    dataset_path = find_dataset()
    if not dataset_path:
        print("❌ Crop recommendation dataset not found!")
        print("   Run 'python download_datasets.py' first.")
        sys.exit(1)

    print(f"🔄 Loading dataset: {dataset_path}")
    df = pd.read_csv(dataset_path)

    # Expected columns: N, P, K, temperature, humidity, ph, rainfall, label
    features = ['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']
    
    if not all(col in df.columns for col in features + ['label']):
        print("❌ Dataset missing expected columns.")
        sys.exit(1)

    X = df[features]
    y = df['label']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("🧠 Training RandomForestClassifier...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    
    print(f"\n✅ Training Complete! Accuracy: {acc * 100:.2f}%\n")
    print("Classification Report Overview:")
    # Print a condensed report
    report = classification_report(y_test, y_pred, output_dict=True)
    for k, v in list(report.items())[:5]:
        if isinstance(v, dict):
            print(f"  {k:15s} : F1={v['f1-score']:.2f}")

    model_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(model_dir, "crop_model.joblib")
    joblib.dump(model, out_path)
    
    print(f"\n📦 Model saved to: {out_path}")

if __name__ == "__main__":
    train()
