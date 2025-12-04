import os
import torch
from ultralytics import YOLO
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PlanetDetector:
    def __init__(self, model_path="models/planet_yolo_v8.pt"):
        self.model_path = model_path
        self.model = None
        self.initialize_model()

    def initialize_model(self):
        """Initialize the YOLO model"""
        try:
            if os.path.exists(self.model_path):
                logger.info(f"Loading YOLO model from {self.model_path}")
                self.model = YOLO(self.model_path)
                logger.info("✅ Planet detection model loaded successfully")
            else:
                logger.warning(f"⚠️ Model file not found at {self.model_path}. Detection will not work until trained.")
                self.model = None
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            self.model = None

    def detect_and_classify_planets(self, image_path, conf_threshold=0.25):
        """
        Detect planets in an image.
        
        Args:
            image_path (str): Path to the image file.
            conf_threshold (float): Confidence threshold for detections.
            
        Returns:
            dict: Detection results including bounding boxes and classes.
        """
        if self.model is None:
            # Try to reload in case it was just trained
            self.initialize_model()
            if self.model is None:
                return {'error': 'Model not loaded. Please train the model first.'}

        try:
            # Run inference
            results = self.model(image_path, conf=conf_threshold)[0]
            
            detections = []
            
            for box in results.boxes:
                # Get box coordinates
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                
                # Get confidence and class
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_name = results.names[cls_id]
                
                detections.append({
                    'bbox': {
                        'x1': int(x1),
                        'y1': int(y1),
                        'x2': int(x2),
                        'y2': int(y2),
                        'width': int(x2 - x1),
                        'height': int(y2 - y1)
                    },
                    'confidence': round(conf, 2),
                    'class_id': cls_id,
                    'class_name': cls_name
                })
            
            # Sort by confidence (descending)
            detections.sort(key=lambda x: x['confidence'], reverse=True)
            
            return {
                'success': True,
                'count': len(detections),
                'detections': detections
            }
            
        except Exception as e:
            logger.error(f"Error during detection: {e}")
            return {'error': str(e)}

def initialize_detection_system():
    """Factory function to create and return the detector instance"""
    return PlanetDetector()
