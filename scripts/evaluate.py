import os
import glob
import cv2
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.identification.model_loader import PlanetDetector

# Configuration
TEST_DIR = r"D:\Coding\MajorServer\samples"
OUTPUT_DIR = r"D:\Coding\MajorServer\samples\debug"
MODEL_PATH = r"D:\Coding\MajorServer\models\planet_yolo_v8.pt"

def test_model():
    print(f"--- Testing Model on {TEST_DIR} ---")
    
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Model not found at {MODEL_PATH}")
        return

    detector = PlanetDetector(MODEL_PATH)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    image_files = glob.glob(os.path.join(TEST_DIR, "*.*"))
    image_files = [f for f in image_files if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    print(f"Found {len(image_files)} test images.")
    
    for img_path in image_files:
        filename = os.path.basename(img_path)
        print(f"\nProcessing: {filename}")
        
        # Run detection
        result = detector.detect_and_classify_planets(img_path, conf_threshold=0.25)
        
        if 'error' in result:
            print(f"  Error: {result['error']}")
            continue
            
        print(f"  Found {result.get('count', 0)} planets.")
        
        # Draw bounding boxes
        img = cv2.imread(img_path)
        if img is None:
            print("  Failed to load image.")
            continue
            
        for det in result.get('detections', []):
            bbox = det['bbox']
            cls = det['class_name']
            conf = det['confidence']
            
            x1, y1 = bbox['x1'], bbox['y1']
            x2, y2 = bbox['x2'], bbox['y2']
            
            # Draw box
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw label
            label = f"{cls} {conf:.2f}"
            cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            
            print(f"    - {cls} ({conf:.2f}) at [{x1}, {y1}, {x2}, {y2}]")
            
        # Save debug image
        save_path = os.path.join(OUTPUT_DIR, f"debug_{filename}")
        cv2.imwrite(save_path, img)
        print(f"  Saved debug image to {save_path}")

if __name__ == "__main__":
    test_model()
