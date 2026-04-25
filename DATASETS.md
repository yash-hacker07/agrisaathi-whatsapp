# 📊 AgriSaathi — Training Datasets

## Quick Setup

```bash
# 1. Make sure you have Kaggle CLI configured
#    Place your kaggle.json in ~/.kaggle/ (Linux/Mac) or %USERPROFILE%\.kaggle\ (Windows)

# 2. Run the auto-download script
python download_datasets.py
```

---

## Dataset Details

### 1. 🌾 Crop Recommendation Dataset
- **Purpose**: Train RandomForest model → predict best crop from soil + weather data
- **Size**: ~2.2K rows, 8 columns
- **Features**: N, P, K, temperature, humidity, pH, rainfall → crop label (22 crops)
- **Kaggle**: https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset
- **CLI**: `kaggle datasets download -d atharvaingle/crop-recommendation-dataset`

### 2. 🍃 PlantVillage Disease Dataset  
- **Purpose**: Train CNN (MobileNetV2) → classify leaf diseases from photos
- **Size**: 54,305 images across 38 classes (14 crop species)
- **Classes include**: Apple_scab, Tomato_Early_blight, Rice_Blast, Potato_Late_blight, etc.
- **Kaggle**: https://www.kaggle.com/datasets/abdallahalidev/plantvillage-dataset
- **CLI**: `kaggle datasets download -d abdallahalidev/plantvillage-dataset`

### 3. 🌿 Rice Leaf Diseases
- **Purpose**: Supplementary rice-specific disease detection
- **Size**: 120 images (Bacterial Blight, Blast, Brown Spot)
- **Kaggle**: https://www.kaggle.com/datasets/vbookshelf/rice-leaf-diseases
- **CLI**: `kaggle datasets download -d vbookshelf/rice-leaf-diseases`

### 4. 🐛 Pest Dataset for Crop Protection
- **Purpose**: Pest image identification
- **Size**: 4,500+ pest images across 12 classes
- **Kaggle**: https://www.kaggle.com/datasets/simranvolunesia/pest-dataset
- **CLI**: `kaggle datasets download -d simranvolunesia/pest-dataset`

### 5. 📈 Indian Crop Production Statistics
- **Purpose**: Yield prediction and crop rotation recommendations
- **Size**: 246K+ rows of state/district level production data
- **Kaggle**: https://www.kaggle.com/datasets/abhinand05/crop-production-in-india
- **CLI**: `kaggle datasets download -d abhinand05/crop-production-in-india`

---

## Manual Download (if Kaggle CLI not set up)

1. Visit each Kaggle link above
2. Click **Download** button
3. Extract ZIP files into `datasets/` folder:

```
agrisaathi-core-features/
  datasets/
    crop-recommendation/
      Crop_recommendation.csv
    plantvillage/
      color/          ← Use this folder
        Apple___Apple_scab/
        Apple___Black_rot/
        ...
    rice-leaf-diseases/
    pest-dataset/
    crop-production-india/
```
