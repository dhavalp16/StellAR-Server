import os
import time
import glob
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import uuid
from threading import Thread
import logging
import shutil
import json
import sys
from pathlib import Path
import torch
import gc
from flask_jwt_extended import JWTManager
from modules.models import db, User, Model
from modules.auth import auth_bp

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules', 'identification'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
OUTPUT_DIR = "models"
GENERATED_DIR = "generated_models"
COMFYUI_OUTPUT_DIR = "C:/ComfyUI_windows_portable/ComfyUI/output/"
Path(OUTPUT_DIR).mkdir(exist_ok=True)
Path(GENERATED_DIR).mkdir(exist_ok=True)

# Database & Auth Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'super-secret-key-change-this-in-prod'  # Change this!
app.config['OUTPUT_DIR'] = OUTPUT_DIR
app.config['GENERATED_DIR'] = GENERATED_DIR
app.config['COMFYUI_OUTPUT_DIR'] = COMFYUI_OUTPUT_DIR
app.config['SUPABASE_URL'] = os.environ.get('SUPABASE_URL')
app.config['SUPABASE_KEY'] = os.environ.get('SUPABASE_KEY')


# Initialize Extensions
db.init_app(app)
jwt = JWTManager(app)

# JWT Error Handlers
@jwt.invalid_token_loader
def invalid_token_callback(error):
    print(f"❌ INVALID TOKEN: {error}")
    return jsonify({"msg": "Invalid token", "error": str(error)}), 422

@jwt.unauthorized_loader
def missing_token_callback(error):
    print(f"❌ MISSING TOKEN: {error}")
    return jsonify({"msg": "Request does not contain an access token", "error": str(error)}), 401

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    print(f"❌ EXPIRED TOKEN: {jwt_payload}")
    return jsonify({"msg": "Token has expired", "error": "token_expired"}), 401

# Register Blueprints
app.register_blueprint(auth_bp)

from modules.api.scan import scan_bp
from modules.api.models import models_bp
from modules.api.users import users_bp
from modules.api.classroom import classroom_api
from modules.api.llm_response import llm_api


app.register_blueprint(scan_bp)
app.register_blueprint(models_bp)
app.register_blueprint(users_bp)
app.register_blueprint(classroom_api)
app.register_blueprint(llm_api)

# Create Tables
with app.app_context():
    db.create_all()

# Import modules with error handling
# We attach them to 'app' so blueprints can access them via current_app
app.planet_detector = None
app.comfy_client = None
app.model_manager = None

def initialize_modules():
    """Initialize all modules with proper error handling"""
    try:
        # Print GPU info
        if torch.cuda.is_available():
            gpu_props = torch.cuda.get_device_properties(0)
            print(f"✅ GPU Detected: {torch.cuda.get_device_name(0)}")
            print(f"📊 GPU Memory: {gpu_props.total_memory / 1024**3:.1f} GB")
            print(f"🔧 CUDA Version: {torch.version.cuda}")
        else:
            print("❌ No GPU detected - using CPU (slow)")
        
        # Try to initialize planet detector
        try:
            from modules.identification.model_loader import initialize_detection_system
            app.planet_detector = initialize_detection_system()
        except Exception as e:
            print(f"⚠️ Planet detector not available: {e}")
        
        # Initialize ComfyUI client with error handling
        try:
            from modules.generation.comfyui_client import ComfyUIClient
            app.comfy_client = ComfyUIClient()
        except Exception as e:
            print(f"⚠️ ComfyUI client not available: {e}")
        
        # Initialize model manager
        try:
            from modules.generation.model_manager import ModelManager
            # Pass the configured GENERATED_DIR
            app.model_manager = ModelManager(models_dir=app.config['GENERATED_DIR'])
        except Exception as e:
            print(f"⚠️ Model manager not available: {e}")
        
        print("✅ All available modules loaded!")
        
        # Initialize Supabase
        try:
            from modules.supabase_service import supabase_service
            supabase_service.initialize()
        except Exception as e:
            logger.warning(f"Supabase init failed: {e}")

            
    except Exception as e:
        logger.warning(f"Error loading modules: {e}")

# Initialize modules
initialize_modules()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/gpu_status')
def gpu_status():
    """Endpoint to check GPU status"""
    if torch.cuda.is_available():
        gpu_props = torch.cuda.get_device_properties(0)
        allocated = torch.cuda.memory_allocated() / 1024**3
        cached = torch.cuda.memory_reserved() / 1024**3
        return jsonify({
            'available': True,
            'gpu_name': torch.cuda.get_device_name(0),
            'memory_total': round(gpu_props.total_memory / 1024**3, 1),
            'memory_allocated': round(allocated, 1),
            'memory_cached': round(cached, 1),
            'memory_available': round(gpu_props.total_memory / 1024**3 - allocated, 1)
        })
    else:
        return jsonify({'available': False})

if __name__ == '__main__':
    print("🚀 Starting MajorServer with RTX 3060 Optimization...")
    print("💡 Make sure ComfyUI is running on http://127.0.0.1:8188")
    print("📊 GPU monitoring available at /gpu_status")
    app.run(debug=True, port=5000, host='0.0.0.0')