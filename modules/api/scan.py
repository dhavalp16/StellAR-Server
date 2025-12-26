from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import uuid
from modules.models import db, User
# We need to access the global planet_detector from app context or a shared module
# Ideally, we should move the detector initialization to a shared location or use current_app
from flask import current_app
from modules.api.llm_response import generate_info_internal

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "starcoder2:3b"

scan_bp = Blueprint('scan', __name__, url_prefix='/api/scan')

@scan_bp.route('', methods=['POST'])
# @jwt_required()
def scan_image():
    """
    Upload an image -> Detect Planets -> Generate Info via LLM for ALL detections -> Return Combined Data
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    # Access detector from app config/context
    detector = current_app.planet_detector
    
    if not detector:
        return jsonify({'error': 'Detection system not initialized'}), 500
        
    # Save temp file
    temp_id = str(uuid.uuid4())
    output_dir = current_app.config.get('OUTPUT_DIR', 'temp_uploads') 
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    temp_path = os.path.join(output_dir, f"temp_scan_{temp_id}.png")
    file.save(temp_path)
    
    try:
        # 1. Run detection
        result = detector.detect_and_classify_planets(temp_path)
        
        # Cleanup immediately
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        if 'error' in result:
            return jsonify({'error': result['error']}), 500
            
        # 2. Process detections
        detections = []
        detected_names = []
        best_match_name = None
        highest_confidence = 0.0

        for d in result.get('detections', []):
            conf = d.get('confidence', 0)
            if conf > 0.9:  # Confidence threshold
                class_name = d['class_name']
                detections.append({
                    'name': class_name,
                    'confidence': conf,
                    'bbox': d.get('bbox')
                })
                detected_names.append(class_name)
                
                if conf > highest_confidence:
                    highest_confidence = conf
                    best_match_name = class_name
        
        # 3. Generate Info for ALL detected objects
        llm_info = []
        if detected_names:
            try:
                print(f"Generating info for detected objects: {detected_names}")
                # Pass all detected names to generate info for each one
                llm_info = generate_info_internal(detected_names)
            except Exception as e:
                print(f"LLM Generation failed: {e}")
                # Fallback: create empty info for each detection
                llm_info = [{
                    "title": name,
                    "summary": "Could not generate information at this time.",
                    "facts": ["Data unavailable", "Data unavailable", "Data unavailable"],
                    "error": str(e)
                } for name in detected_names]

        # 4. Construct Final Response
        response_data = {
            'success': True,
            'detections': detections,
            'best_match': best_match_name,
            'info': llm_info,  # Now returns array of info objects
            'count': len(detections)
        }
        print(response_data)
        
        return jsonify(response_data), 200
        
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        print(f"Scan Error: {e}")
        return jsonify({'error': str(e)}), 500