from flask import Blueprint, request, jsonify, current_app
import os
import uuid
import json
from werkzeug.utils import secure_filename
from modules.supabase_service import supabase_service
import threading
import shutil

learning_modules_bp = Blueprint('learning_modules_bp', __name__)

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}


def allowed_file(filename, allowed_extensions):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower().strip()
    return ext in allowed_extensions


def run_model_generation_task(app, job_id, image_path):
    """
    Background task for ComfyUI 3D model generation.
    Uploads generated model to Supabase and stores the URL.
    """
    with app.app_context():
        try:
            comfy = app.comfy_client
            
            # 1. Upload Input Image to ComfyUI (for processing)
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
                # Save to GENERATED_DIR
                dest_path = os.path.join(app.config['GENERATED_DIR'], filename)
                shutil.move(final_glb, dest_path)
                
                # Upload to Supabase Storage
                model_url = supabase_service.upload_file("models", dest_path, filename)
                print(f"✓ Uploaded Model to Supabase: {model_url}")
                
                # Store result in app context for retrieval
                if not hasattr(app, 'generation_results'):
                    app.generation_results = {}
                app.generation_results[job_id] = {
                    'status': 'completed',
                    'model_url': model_url
                }
                        
            print(f"Generation job {job_id} complete")
                
        except Exception as e:
            print(f"Generation job {job_id} failed: {e}")
            if not hasattr(app, 'generation_results'):
                app.generation_results = {}
            app.generation_results[job_id] = {
                'status': 'failed',
                'error': str(e)
            }
        finally:
            if os.path.exists(image_path):
                os.remove(image_path)


@learning_modules_bp.route('/api/generate_model', methods=['POST'])
def generate_model():
    """
    Generate a 3D model from an image.
    Steps:
    1. Accept image file upload.
    2. Trigger 3D model generation via ComfyUI.
    3. Upload generated model to Supabase storage bucket.
    4. Return the model URL.
    """
    try:
        # 1. Validate Files
        if 'image' not in request.files:
            return jsonify({'error': 'Missing image file'}), 400

        image_file = request.files['image']

        if image_file.filename == '':
            return jsonify({'error': 'No image file selected'}), 400

        if not allowed_file(image_file.filename, ALLOWED_IMAGE_EXTENSIONS):
            return jsonify({'error': f'Invalid image file type: {image_file.filename}. Allowed: {", ".join(ALLOWED_IMAGE_EXTENSIONS)}'}), 400

        # 2. Save image temporarily
        job_id = str(uuid.uuid4())
        output_dir = current_app.config.get('OUTPUT_DIR', 'models')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        image_filename = secure_filename(image_file.filename)
        temp_image_path = os.path.join(output_dir, f"temp_gen_{job_id}_{image_filename}")
        image_file.save(temp_image_path)

        print(f"DEBUG: Processing image - {image_file.filename}, Job ID: {job_id}")

        # 3. Initialize generation results storage
        if not hasattr(current_app, 'generation_results'):
            current_app.generation_results = {}
        current_app.generation_results[job_id] = {'status': 'processing'}

        # 4. Trigger 3D Model Generation in background
        thread = threading.Thread(
            target=run_model_generation_task, 
            args=(
                current_app._get_current_object(), 
                job_id, 
                temp_image_path
            )
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            "success": True,
            "message": "3D model generation started",
            "job_id": job_id
        }), 202

    except Exception as e:
        return jsonify({'error': f"Server error: {str(e)}"}), 500


@learning_modules_bp.route('/api/generation_status/<job_id>', methods=['GET'])
def get_generation_status(job_id):
    """
    Get the status of a model generation job.
    Returns the model URL when complete.
    """
    try:
        if not hasattr(current_app, 'generation_results'):
            return jsonify({'error': 'Job not found'}), 404
            
        result = current_app.generation_results.get(job_id)
        
        if not result:
            return jsonify({'error': 'Job not found'}), 404
            
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': f"Server error: {str(e)}"}), 500
