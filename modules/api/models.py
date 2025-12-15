from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from modules.models import db, Model, User
import os
import uuid
import time
import threading
import json

# Change prefix to /api to allow /api/models and /api/modelurl
models_bp = Blueprint('models', __name__, url_prefix='/api')

# --- 1. GET /api/models ---
@models_bp.route('/models', methods=['GET'])
def list_models():
    """List models filtered by subject"""
    try:
        from modules.supabase_service import supabase_service
        
        subject = request.args.get('subject')
        
        # Build query
        # We want speicific fields: model_id, model_name, description, rarity, model_subject, model_thumbnail, xp_reward
        # Supabase 'select' can do this.
        
        filters = {}
        if subject:
            filters['model_subject'] = subject
            
        models = supabase_service.query_records("models", select="*", filters=filters)
        
        # Transform logic if necessary, otherwise return as is.
        # The user requested specific JSON structure. Supabase returns list of dicts.
        # We can map it to be safe or return direct if columns match.
        # User requested: model_id, model_name, description, rarity, model_subject, model_thumbnail, xp_reward
        # Our schema has these exact columns.
        
        return jsonify(models)
        
    except Exception as e:
        print(f"❌ Error listing models: {e}")
        return jsonify({'error': str(e)}), 500

# --- 2. GET /api/modelurl ---
@models_bp.route('/modelurl', methods=['GET'])
def get_model_url():
    """Fetch specific 3D asset URL"""
    try:
        from modules.supabase_service import supabase_service
        
        model_id = request.args.get('model_id')
        if not model_id:
            return jsonify({'error': 'model_id is required'}), 400
            
        # Query Supabase: select model_url from models where model_id = model_id
        # query_records returns a list
        results = supabase_service.query_records("models", select="model_url", filters={"model_id": model_id})
        
        if not results:
            return jsonify({'error': 'Model not found'}), 404
            
        return jsonify(results[0])
        
    except Exception as e:
        print(f"❌ Error getting model url: {e}")
        return jsonify({'error': str(e)}), 500


# --- Legacy/Local Routes (Optional/Fallback) ---

@models_bp.route('/models/<int:model_id>/download', methods=['GET'])
@jwt_required()
def download_model(model_id):
    """(Legacy) Download local .glb file"""
    model = Model.query.get_or_404(model_id)
    # ... existing permissions logic ...
    user_id = int(get_jwt_identity())
    if not model.is_public and model.uploader_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    if not os.path.exists(model.file_path):
        return jsonify({'error': 'File not found on server'}), 404
    return send_file(model.file_path, as_attachment=True, download_name=f"{model.name}.glb")


# --- Generation Logic ---

@models_bp.route('/models/generate', methods=['POST'])
@jwt_required()
def generate_model():
    """Trigger 3D generation task"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
        
    file = request.files['file']
    prompt = request.form.get('prompt', 'planet') 
    name_input = request.form.get('name') 
    subject_input = request.form.get('subject', 'Astronomy') # Default subject
    
    comfy_client = current_app.comfy_client
    if not comfy_client:
        return jsonify({'error': 'Generation service unavailable'}), 503
        
    # Save temp input
    job_id = str(uuid.uuid4())
    output_dir = current_app.config.get('OUTPUT_DIR', 'models')
    input_path = os.path.join(output_dir, f"temp_gen_input_{job_id}.png")
    file.save(input_path)
    
    # Get user ID
    user_id = int(get_jwt_identity())

    thread = threading.Thread(target=run_generation_task, 
                            args=(current_app._get_current_object(), job_id, input_path, user_id, name_input, subject_input))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'status': 'processing',
        'message': 'Generation started.'
    })

def calculate_rarity():
    import random
    roll = random.random()
    if roll < 0.05: return "Legendary", 500
    elif roll < 0.20: return "Epic", 150
    elif roll < 0.50: return "Rare", 50
    else: return "Common", 10

def run_generation_task(app, job_id, image_path, user_id, user_provided_name=None, subject='Astronomy'):
    """Background task for ComfyUI generation"""
    with app.app_context():
        try:
            comfy = app.comfy_client
            
            # 1. Upload Input Image to ComfyUI (for processing)
            image_filename = comfy.upload_image(image_path)
            
            # --- SUPABASE: Upload Thumbnail ---
            # Use the input image as the thumbnail
            from modules.supabase_service import supabase_service
            thumbnail_url = ""
            if supabase_service.initialized:
                try:
                    # Upload input image to 'models' bucket as thumbnail
                    thumb_name = f"thumb_{job_id}.png"
                    thumbnail_url = supabase_service.upload_file("models", image_path, thumb_name)
                except Exception as e:
                    print(f"⚠️ Thumbnail upload failed: {e}")

            # 2. Load Workflow
            wf_path = os.path.join('workflows', 'hunyuan_workflow_api.json')
            if not os.path.exists(wf_path):
                wf_path = os.path.join('workflows', 'hunyuan_workflow.json')
                
            with open(wf_path, 'r') as f:
                workflow = json.load(f)
                
            # 3. Modify Workflow
            for node in workflow.values():
                if node.get('class_type') == 'LoadImage':
                    node['inputs']['image'] = image_filename
            
            target_prefix = f"gen_{job_id}"
            for node in workflow.values():
                if 'filename_prefix' in node.get('inputs', {}):
                    node['inputs']['filename_prefix'] = target_prefix
                    
            # 4. Queue & Wait
            comfy.queue_prompt(workflow)
            
            comfy_output_dir = app.config.get('COMFYUI_OUTPUT_DIR')
            search_pattern = os.path.join(comfy_output_dir, f"{target_prefix}*.glb")
            
            final_glb = comfy.wait_for_completion(search_pattern)
            
            if final_glb:
                filename = os.path.basename(final_glb)
                # Save to GENERATED_DIR
                dest_path = os.path.join(app.config['GENERATED_DIR'], filename)
                import shutil
                shutil.move(final_glb, dest_path)
                
                # Determine Final Name
                final_name = user_provided_name if user_provided_name else f"Generated Model {job_id[:8]}"
                
                # --- SUPABASE INTEGRATION ---
                try:
                    if supabase_service.initialized:
                        # Upload Model File
                        model_url = supabase_service.upload_file("models", dest_path, filename)
                        print(f"✓ Uploaded Model to Supabase: {model_url}")
                        
                        # Calculate Rarity
                        rarity_name, xp_val = calculate_rarity()
                        
                        # Insert Record
                        # Schema: model_name, description, model_url, rarity, xp_reward, metadata, model_subject, model_thumbnail, min_level
                        record = {
                            "model_name": final_name,
                            "description": "Generated via ComfyUI",
                            "model_url": model_url,
                            "rarity": rarity_name,
                            "xp_reward": xp_val,
                            "model_subject": subject,
                            "model_thumbnail": thumbnail_url,
                            "min_level": 1, 
                            "uploader_id": str(uuid.uuid4()), # Placeholder UUID or real user UUID if linked
                            "metadata": {
                                "job_id": job_id,
                                "prompt": "Generated"
                            }
                        }
                        
                        # Note: uploader_id in new schema is UUID. 'user_id' from JWT was int (from SQLite).
                        # If we are mixing systems, we might need a valid UUID. 
                        # For now, generating a random one or handling it at DB level if nullable.
                        # User schema says 'uploader_id' (uuid).
                        
                        supabase_service.insert_record("models", record)
                        print(f"✓ Record inserted into Supabase DB")
                    else:
                        print("⚠️ Supabase not initialized.")
                        
                except Exception as e:
                    print(f"⚠️ Supabase processing failed: {e}")
                    # Fallback to local DB (using old schema? might fail if table changed)
                    # We skip fallback for now as schema diverged too much.

            print(f"Job {job_id} complete: {dest_path}")
                
        except Exception as e:
            print(f"Job {job_id} failed: {e}")
        finally:
            if os.path.exists(image_path):
                os.remove(image_path)
