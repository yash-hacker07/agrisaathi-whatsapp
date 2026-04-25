"""
AgriSaathi — Dataset Downloader
================================
Downloads all training datasets from Kaggle into the datasets/ directory.

Prerequisites:
  1. pip install kaggle
  2. Place your kaggle.json API token in:
     - Windows: %USERPROFILE%\.kaggle\kaggle.json
     - Linux/Mac: ~/.kaggle/kaggle.json
  
  Get your token from: https://www.kaggle.com/settings → API → Create New Token

Usage:
  python download_datasets.py
"""

import os
import sys
import zipfile
import shutil

# Directory where datasets will be stored
DATASET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets")

DATASETS = [
    {
        "name": "Crop Recommendation",
        "slug": "atharvaingle/crop-recommendation-dataset",
        "folder": "crop-recommendation",
        "required": True,
    },
    {
        "name": "PlantVillage Disease (54K images)",
        "slug": "abdallahalidev/plantvillage-dataset",
        "folder": "plantvillage",
        "required": True,
    },
    {
        "name": "Rice Leaf Diseases",
        "slug": "vbookshelf/rice-leaf-diseases",
        "folder": "rice-leaf-diseases",
        "required": False,
    },
    {
        "name": "Pest Dataset",
        "slug": "simranvolunesia/pest-dataset",
        "folder": "pest-dataset",
        "required": False,
    },
    {
        "name": "Indian Crop Production",
        "slug": "abhinand05/crop-production-in-india",
        "folder": "crop-production-india",
        "required": False,
    },
]


def check_kaggle_setup():
    """Verify Kaggle API is configured."""
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        print("✅ Kaggle API authenticated successfully")
        return api
    except Exception as e:
        print(f"❌ Kaggle API Error: {e}")
        print("\n📋 Setup Instructions:")
        print("   1. Go to https://www.kaggle.com/settings")
        print("   2. Scroll to 'API' section → Click 'Create New Token'")
        print("   3. Save kaggle.json to:")
        if sys.platform == "win32":
            print(f"      %USERPROFILE%\\.kaggle\\kaggle.json")
        else:
            print(f"      ~/.kaggle/kaggle.json")
        print("   4. Run this script again")
        return None


def download_dataset(api, dataset_info):
    """Download and extract a single dataset."""
    name = dataset_info["name"]
    slug = dataset_info["slug"]
    folder = os.path.join(DATASET_DIR, dataset_info["folder"])

    # Skip if already downloaded
    if os.path.exists(folder) and os.listdir(folder):
        print(f"  ⏭️  {name} — already exists, skipping")
        return True

    print(f"  📥 Downloading {name}...")
    os.makedirs(folder, exist_ok=True)

    try:
        api.dataset_download_files(slug, path=folder, unzip=True)
        print(f"  ✅ {name} — downloaded & extracted")
        return True
    except Exception as e:
        print(f"  ❌ {name} — failed: {e}")
        if not dataset_info["required"]:
            print(f"     (Optional dataset, continuing...)")
        return False


def main():
    print("=" * 60)
    print("🌾 AgriSaathi — Dataset Downloader")
    print("=" * 60)
    print()

    # 1. Check Kaggle setup
    api = check_kaggle_setup()
    if not api:
        sys.exit(1)

    # 2. Create datasets directory
    os.makedirs(DATASET_DIR, exist_ok=True)
    print(f"\n📂 Download directory: {DATASET_DIR}\n")

    # 3. Download each dataset
    success_count = 0
    fail_count = 0
    for ds in DATASETS:
        ok = download_dataset(api, ds)
        if ok:
            success_count += 1
        else:
            fail_count += 1

    # 4. Summary
    print()
    print("=" * 60)
    print(f"📊 Results: {success_count} downloaded, {fail_count} failed")
    print("=" * 60)

    # 5. Show dataset structure
    print("\n📁 Dataset directory structure:")
    for ds in DATASETS:
        folder = os.path.join(DATASET_DIR, ds["folder"])
        if os.path.exists(folder):
            file_count = sum(len(files) for _, _, files in os.walk(folder))
            print(f"   ├── {ds['folder']}/ ({file_count} files)")

    print(f"\n🎯 Next steps:")
    print(f"   1. Train crop model:    python -m mlbackend.train_crop_model")
    print(f"   2. Train disease model: python -m mlbackend.train_disease_model")
    print(f"   3. Start server:        uvicorn mlbackend.main:app --reload")


if __name__ == "__main__":
    main()
