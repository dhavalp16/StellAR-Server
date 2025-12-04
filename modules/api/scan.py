from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import uuid
from modules.models import db, User
# We need to access the global planet_detector from app context or a shared module
# Ideally, we should move the detector initialization to a shared location or use current_app
from flask import current_app

scan_bp = Blueprint('scan', __name__, url_prefix='/api/scan')

@scan_bp.route('', methods=['POST'])
def scan_image():
    """
    Upload an image -> Detect Planets -> Return Metadata
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    # Access detector from app config/context
    # We will attach it to app.planet_detector in app.py
    detector = current_app.planet_detector
    
    if not detector:
        return jsonify({'error': 'Detection system not initialized'}), 500
        
    # Save temp file
    temp_id = str(uuid.uuid4())
    output_dir = current_app.config.get('OUTPUT_DIR', 'models')
    temp_path = os.path.join(output_dir, f"temp_scan_{temp_id}.png")
    file.save(temp_path)
    
    try:
        # Run detection
        result = detector.detect_and_classify_planets(temp_path)
        
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        if 'error' in result:
            return jsonify({'error': result['error']}), 500
            
        # Format response for Unity
        # Unity needs: Class Name, Confidence, Bounding Box (normalized?)
        # The detector returns normalized bbox if configured, or pixel coords.
        # Let's assume pixel coords for now, Unity can handle mapping if we send image size.
        
        detections = []
        for d in result.get('detections', []):
            detections.append({
                'name': d['class_name'],
                'confidence': d['confidence'],
                'bbox': d['bbox']
            })
            
        return jsonify({
            'success': True,
            'detections': detections,
            'count': len(detections)
        })
        
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({'error': str(e)}), 500
