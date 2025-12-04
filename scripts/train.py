import os
import yaml
import shutil
from ultralytics import YOLO
import glob
from sklearn.model_selection import train_test_split

# Configuration
DATA_ROOT = r"D:\Coding\MajorServer\dataset"
IMAGES_DIR = os.path.join(DATA_ROOT, "data", "raw_planets")
LABELS_DIR = os.path.join(DATA_ROOT, "labels")
WORKING_DIR = r"D:\Coding\MajorServer\dataset\yolo_dataset"
MODEL_OUTPUT_DIR = r"D:\Coding\MajorServer\models"

def setup_dataset():
    """Prepare the dataset structure for YOLOv8"""
    print("--- Setting up dataset ---")
    
    # Create YOLO directory structure
    for split in ['train', 'val']:
        os.makedirs(os.path.join(WORKING_DIR, 'images', split), exist_ok=True)
        os.makedirs(os.path.join(WORKING_DIR, 'labels', split), exist_ok=True)
    
    # Gather all image-label pairs
    # We need to match images in raw_planets (recursive) with labels in labels (recursive)
    # The structure is slightly different, so we need to be careful.
    # Images: data/raw_planets/earth/Earth (1).jpg
    # Labels: labels/earth/Earth (1).txt
    
    image_files = []
    for root, dirs, files in os.walk(IMAGES_DIR):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_files.append(os.path.join(root, file))
    
    print(f"Found {len(image_files)} images.")
    
    valid_pairs = []
    
    for img_path in image_files:
        # Construct expected label path
        # Rel path from IMAGES_DIR
        rel_path = os.path.relpath(img_path, IMAGES_DIR)
        # Change extension to .txt
        label_rel_path = os.path.splitext(rel_path)[0] + ".txt"
        label_path = os.path.join(LABELS_DIR, label_rel_path)
        
        if os.path.exists(label_path):
            valid_pairs.append((img_path, label_path))
    
    print(f"Found {len(valid_pairs)} valid image-label pairs.")
    
    if not valid_pairs:
        print("❌ No valid pairs found! Check your paths.")
        return False

    # Split into train/val
    train_pairs, val_pairs = train_test_split(valid_pairs, test_size=0.2, random_state=42)
    
    print(f"Training set: {len(train_pairs)}")
    print(f"Validation set: {len(val_pairs)}")
    
    # Copy files
    def copy_set(pairs, split):
        for img, lbl in pairs:
            # Flatten structure to avoid issues, or keep it? YOLO handles flat well.
            # Let's flatten for simplicity, using unique names if needed.
            # Actually, let's keep filenames but handle duplicates if any?
            # The filenames like "Earth (1).jpg" are unique per folder but maybe not globally?
            # They seem unique enough with the numbering.
            
            fname = os.path.basename(img)
            lname = os.path.basename(lbl)
            
            shutil.copy(img, os.path.join(WORKING_DIR, 'images', split, fname))
            shutil.copy(lbl, os.path.join(WORKING_DIR, 'labels', split, lname))
            
    copy_set(train_pairs, 'train')
    copy_set(val_pairs, 'val')
    
    # Create data.yaml
    # We need the class names list
    classes_file = os.path.join(LABELS_DIR, "classes.txt")
    with open(classes_file, 'r') as f:
        class_names = [line.strip() for line in f.readlines() if line.strip()]
        
    data_config = {
        'path': WORKING_DIR,
        'train': 'images/train',
        'val': 'images/val',
        'names': {i: name for i, name in enumerate(class_names)}
    }
    
    yaml_path = os.path.join(WORKING_DIR, 'data.yaml')
    with open(yaml_path, 'w') as f:
        yaml.dump(data_config, f)
        
    print(f"Dataset prepared at {WORKING_DIR}")
    return yaml_path

def train_model(data_yaml):
    """Train the YOLOv8 model"""
    print("\n--- Starting Training ---")
    
    # Load a model
    model = YOLO('yolov8n.pt')  # load a pretrained model (nano for speed)
    
    # Train the model
    # epochs=50 is a good start. imgsz=640 is standard.
    results = model.train(
        data=data_yaml,
        epochs=30,
        imgsz=640,
        batch=16,
        name='planet_yolo',
        project=WORKING_DIR,
        exist_ok=True,
        device=0
    )
    
    # Save the best model to our server directory
    best_model_path = os.path.join(WORKING_DIR, 'planet_yolo', 'weights', 'best.pt')
    target_path = os.path.join(MODEL_OUTPUT_DIR, 'planet_yolo_v8.pt')
    
    if os.path.exists(best_model_path):
        os.makedirs(MODEL_OUTPUT_DIR, exist_ok=True)
        shutil.copy(best_model_path, target_path)
        print(f"✅ Model saved to {target_path}")
    else:
        print("❌ Training finished but best.pt not found.")

if __name__ == "__main__":
    yaml_path = setup_dataset()
    if yaml_path:
        train_model(yaml_path)
