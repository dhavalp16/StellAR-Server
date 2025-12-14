from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from modules.models import db, Model, User
import os
import uuid
import time
import threading
import json

models_bp = Blueprint('models', __name__, url_prefix='/api/models')

@models_bp.route('/', methods=['GET'])
# @jwt_required() # Disabled for specific demo ease if needed, but keeping security best practice
def list_models():
    """List all available models (Public + User's own)"""
    
    # --- Supabase Integration ---
    from modules.supabase_service import supabase_service
    
    # Try Supabase First (Source of Truth for Cloud Models)
    supabase_models = supabase_service.query_records("models", select="*")
    
    if supabase_models:
        # Transform to expected format if needed, or return as is
        # Supabase returns dicts matching the DB schema
        return jsonify(supabase_models)
    
    # --- Fallback to Local DB (Legacy/Offline) ---
    # Only if Supabase is down or empty
    try:
        user_id = int(get_jwt_identity())
    except:
        user_id = None # Anonymous/Public only
        
    public_models = Model.query.filter_by(is_public=True).all()
    if user_id:
        user_models = Model.query.filter_by(uploader_id=user_id).all()
        all_models = list(set(public_models + user_models))
    else:
        all_models = public_models
        
    result = []
    for m in all_models:
        result.append({
            'id': m.id,
            'name': m.name,
            'description': m.description,
            'source': m.source,
            'created_at': m.created_at.isoformat(),
            'storage_url': None # Local models don't have a public URL usually
        })
        
    return jsonify(result)

# --- Helpers ---
def calculate_rarity():
    import random
    roll = random.random() # 0.0 to 1.0
    
    if roll < 0.05: # 5% chance
        return "Legendary", 500
    elif roll < 0.20: # 15% chance
        return "Epic", 150
    elif roll < 0.50: # 30% chance
        return "Rare", 50
    else: # 50% chance
        return "Common", 10

# ... (Existing download_model code) ...
@jwt_required()
def download_model(model_id):
    """Download the .glb file for a model"""
    model = Model.query.get_or_404(model_id)
    
    # Check permissions (is public or owns it)
    user_id = int(get_jwt_identity())
    if not model.is_public and model.uploader_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    if not os.path.exists(model.file_path):
        return jsonify({'error': 'File not found on server'}), 404
        
    return send_file(model.file_path, as_attachment=True, download_name=f"{model.name}.glb")

# --- Generation Logic ---
# We reuse the logic from app.py but wrapped in an API endpoint

@models_bp.route('/generate', methods=['POST'])
@jwt_required()
def generate_model():
    """Trigger 3D generation task"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
        
    file = request.files['file']
    prompt = request.form.get('prompt', 'planet') # Optional text prompt
    name_input = request.form.get('name') # User provided name
    
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

    # Start background thread
    # Note: In a real prod app, use Celery/Redis. For this prototype, Thread is fine.
    thread = threading.Thread(target=run_generation_task, 
                            args=(current_app._get_current_object(), job_id, input_path, user_id, name_input))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'status': 'processing',
        'message': 'Generation started. Check your library in a few minutes.'
    })

def run_generation_task(app, job_id, image_path, user_id, user_provided_name=None):
    """Background task for ComfyUI generation"""
    with app.app_context():
        try:
            comfy = app.comfy_client
            
            # ... (Upload and Workflow setup skipped for brevity as they are unchanged) ...
            # 1. Upload
            image_filename = comfy.upload_image(image_path)
            
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
                dest_path = os.path.join(app.config['GENERATED_DIR'], filename)
                import shutil
                shutil.move(final_glb, dest_path)
                
                # Determine Final Name
                final_name = user_provided_name if user_provided_name else f"Generated Model {job_id[:8]}"
                
                # --- SUPABASE INTEGRATION ---
                try:
                    from modules.supabase_service import supabase_service
                    
                    if supabase_service.initialized:
                        public_url = supabase_service.upload_file("models", dest_path, filename)
                        print(f"✓ Uploaded to Supabase: {public_url}")
                        
                        # 2. Insert to DB
                        rarity_name, xp_val = calculate_rarity()
                        print(f"🎲 Rarity Roll: {rarity_name} ({xp_val} XP)")
                        
                        record = {
                            "name": final_name,
                            "storage_url": public_url,
                            "rarity": rarity_name,
                            "xp_reward": xp_val,
                            "uploader_id": user_id,
                            "metadata": {
                                "prompt": "Generated via ComfyUI", 
                                "job_id": job_id
                            }
                        }
                        supabase_service.insert_record("models", record)
                        print(f"✓ Record inserted into Supabase DB")
                    else:
                        print("⚠️ Supabase not initialized, skipping upload.")
                        raise Exception("Supabase not init") # Trigger fallback
                        
                except Exception as e:
                    print(f"⚠️ Supabase upload failed: {e}")
                    # Fallback to local
                    new_model = Model(
                        name=final_name,
                        description="Generated from 2D image",
                        file_path=dest_path,
                        source='generated',
                        is_public=False,
                        uploader_id=user_id
                    )
                    db.session.add(new_model)
                    db.session.commit()

            print(f"Job {job_id} complete: {dest_path}")
                
        except Exception as e:
            print(f"Job {job_id} failed: {e}")
        finally:
            if os.path.exists(image_path):
                os.remove(image_path)

