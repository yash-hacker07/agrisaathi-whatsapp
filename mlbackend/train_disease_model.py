"""
AgriSaathi — Disease CNN Training (MobileNetV2 on PlantVillage)
Usage: python -m mlbackend.train_disease_model
"""
import os, sys, json, argparse
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

def find_dataset():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for sub in ["color", "plantvillage dataset/color", "PlantVillage", ""]:
        p = os.path.join(base, "datasets", "plantvillage", sub) if sub else os.path.join(base, "datasets", "plantvillage")
        if os.path.exists(p):
            dirs = [d for d in os.listdir(p) if os.path.isdir(os.path.join(p, d))]
            if len(dirs) >= 5:
                return p
    return None

def train(epochs=10, batch_size=32):
    from tensorflow.keras.applications import MobileNetV2
    from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
    from tensorflow.keras.models import Model
    from tensorflow.keras.preprocessing.image import ImageDataGenerator
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

    print("=" * 60)
    print("🌿 AgriSaathi — Disease Model Training (MobileNetV2)")
    print("=" * 60)

    ds_dir = find_dataset()
    if not ds_dir:
        print("❌ PlantVillage dataset not found! Run download_datasets.py first.")
        sys.exit(1)

    classes = sorted([d for d in os.listdir(ds_dir) if os.path.isdir(os.path.join(ds_dir, d))])
    print(f"📂 Dataset: {ds_dir}")
    print(f"📊 {len(classes)} classes found")

    datagen = ImageDataGenerator(
        rescale=1./255, rotation_range=20, horizontal_flip=True,
        width_shift_range=0.2, height_shift_range=0.2,
        zoom_range=0.15, validation_split=0.2
    )
    train_gen = datagen.flow_from_directory(ds_dir, target_size=(224,224), batch_size=batch_size, class_mode='categorical', subset='training')
    val_gen = datagen.flow_from_directory(ds_dir, target_size=(224,224), batch_size=batch_size, class_mode='categorical', subset='validation')

    base = MobileNetV2(weights='imagenet', include_top=False, input_shape=(224,224,3))
    base.trainable = False
    x = GlobalAveragePooling2D()(base.output)
    x = Dropout(0.3)(x)
    x = Dense(256, activation='relu')(x)
    x = Dropout(0.2)(x)
    out = Dense(len(classes), activation='softmax')(x)
    model = Model(inputs=base.input, outputs=out)
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

    model_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(model_dir, "disease_model.h5")
    labels_path = os.path.join(model_dir, "class_labels.json")

    history = model.fit(
        train_gen, validation_data=val_gen, epochs=epochs,
        callbacks=[
            EarlyStopping(monitor='val_accuracy', patience=3, restore_best_weights=True),
            ModelCheckpoint(model_path, monitor='val_accuracy', save_best_only=True)
        ]
    )

    with open(labels_path, 'w') as f:
        json.dump({str(v): k for k, v in train_gen.class_indices.items()}, f, indent=2)

    print(f"\n✅ Done! Val Accuracy: {max(history.history['val_accuracy'])*100:.1f}%")
    print(f"📦 Model: {model_path} ({os.path.getsize(model_path)/(1024*1024):.1f}MB)")
    print(f"🏷️  Labels: {labels_path}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('--epochs', type=int, default=10)
    p.add_argument('--batch-size', type=int, default=32)
    a = p.parse_args()
    train(a.epochs, a.batch_size)
