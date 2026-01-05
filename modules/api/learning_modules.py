
from flask import Blueprint, request, jsonify, current_app
import os
import uuid
import json
from werkzeug.utils import secure_filename
from modules.api.ocr import extract_text_from_file
from modules.quiz_generator import generate_quiz_from_text, generate_summary_from_text
from modules.supabase_service import supabase_service
from modules.api.models import run_generation_task
import threading

learning_modules_bp = Blueprint('learning_modules_bp', __name__)

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
ALLOWED_MODEL_EXTENSIONS = {'glb', 'obj', 'gltf'}
ALLOWED_PDF_EXTENSIONS = {'pdf'}

def allowed_file(filename, allowed_extensions):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower().strip()
    return ext in allowed_extensions

@learning_modules_bp.route('/api/create_module', methods=['POST'])
def create_module():
    """
    Create a new learning module.
    Steps:
    1. Upload Image and 3D Model to Supabase Storage (bucket: user_uploads).
    2. Extract text from PDF.
    3. Generate Quiz from text.
    4. Insert record into 'classroom_modules' table.
    """
    try:
        # 1. Validate Form Data
        module_name = request.form.get('module_name')
        module_desc = request.form.get('description', '')
        classroom_id = request.form.get('classroom_id')

        if not module_name:
            return jsonify({'error': 'module_name is required'}), 400

        # 2. Validate Files
        if 'image' not in request.files or 'model' not in request.files or 'pdf' not in request.files:
            return jsonify({'error': 'Missing files. Required: image, model, pdf'}), 400

        image_file = request.files['image']
        model_file = request.files['model']
        pdf_file = request.files['pdf']

        print(f"DEBUG: Processing files - Image: {image_file.filename}, Model: {model_file.filename}, PDF: {pdf_file.filename}")

        if image_file.filename == '' or model_file.filename == '' or pdf_file.filename == '':
            return jsonify({'error': 'One or more selected files have no filename'}), 400

        if not allowed_file(image_file.filename, ALLOWED_IMAGE_EXTENSIONS):
            return jsonify({'error': f'Invalid image file type: {image_file.filename}'}), 400
        # Check for GLB magic bytes (handles 'model.bin' case)
        try:
            model_header = model_file.read(4)
            model_file.seek(0)
            is_glb = model_header == b'glTF'
        except Exception as e:
            print(f"DEBUG: Failed to read model header: {e}")
            is_glb = False

        if is_glb:
            # Correct filename if it's a valid GLB but wrong extension
            if not model_file.filename.lower().endswith('.glb'):
                base = os.path.splitext(model_file.filename)[0]
                model_file.filename = f"{base}.glb"
                print(f"DEBUG: Renamed identified GLB file to {model_file.filename}")

        if not is_glb and not allowed_file(model_file.filename, ALLOWED_MODEL_EXTENSIONS):
            return jsonify({'error': f'Invalid model file type: {model_file.filename}'}), 400
        if not allowed_file(pdf_file.filename, ALLOWED_PDF_EXTENSIONS):
            return jsonify({'error': 'Invalid PDF file type'}), 400

        # 3. Save files temporarily
        upload_id = str(uuid.uuid4())
        temp_dir = os.path.join(current_app.config.get('OUTPUT_DIR', 'temp_uploads'), upload_id)
        os.makedirs(temp_dir, exist_ok=True)

        image_filename = secure_filename(image_file.filename)
        model_filename = secure_filename(model_file.filename)
        pdf_filename = secure_filename(pdf_file.filename)

        temp_image_path = os.path.join(temp_dir, image_filename)
        temp_model_path = os.path.join(temp_dir, model_filename)
        temp_pdf_path = os.path.join(temp_dir, pdf_filename)

        image_file.save(temp_image_path)
        model_file.save(temp_model_path)
        pdf_file.save(temp_pdf_path)

        # 4. Upload to Supabase Storage
        try:
            # Upload Image
            image_dest = f"{upload_id}/{image_filename}"
            image_url = supabase_service.upload_file("user_uploads", temp_image_path, image_dest)

            # Upload Model
            model_dest = f"{upload_id}/{model_filename}"
            model_url = supabase_service.upload_file("user_uploads", temp_model_path, model_dest)

        except Exception as e:
            return jsonify({'error': f"Failed to upload to storage: {str(e)}"}), 500

        # 5. Process PDF & Generate Quiz
        try:
            pdf_text = extract_text_from_file(temp_pdf_path)
            # print(pdf_text) # Removed debug print
            quiz_data = generate_quiz_from_text(pdf_text)
            summary_text = generate_summary_from_text(pdf_text)
        except Exception as e:
             return jsonify({'error': f"Failed to process content: {str(e)}"}), 500

        # 6. Insert into Database
        record = {
            "module_name": module_name,
            "module_desc": module_desc,
            "image_url": image_url,
            "model_url": model_url,
            "quiz": quiz_data, # Supabase client should handle JSON serialization
            "summary": summary_text,
            "classroom_id": classroom_id if classroom_id else None 
        }

        try:
            data = supabase_service.insert_record('classroom_modules', record)
        except Exception as e:
             return jsonify({'error': f"Database insertion failed: {str(e)}"}), 500

        # 7. Cleanup
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except:
            pass # Non-critical

        return jsonify({
            "success": True,
            "message": "Module created successfully",
            "data": record
        }), 201

    except Exception as e:
        return jsonify({'error': f"Server error: {str(e)}"}), 500

def trigger_learning_model_generation(image_file, module_name="Generated Learning Asset", module_id=None):
    """
    Helper function to trigger 3D model generation from an image for a learning module.
    Returns a dict with success status and job_id.
    If module_id is provided, updates the classroom_modules record with the model_url when generation completes.
    """
    try:
        # 1. Save Temp Image
        job_id = str(uuid.uuid4())
        output_dir = current_app.config.get('OUTPUT_DIR', 'models')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        input_path = os.path.join(output_dir, f"temp_learn_gen_{job_id}.png")
        image_file.save(input_path)
        
        # 2. Trigger Hunyuan Workflow with callback for learning module
        metadata = {
            "source": "learning_module",
            "type": "generated_asset",
            "module_id": module_id
        }
        
        thread = threading.Thread(
            target=run_learning_generation_task, 
            args=(
                current_app._get_current_object(), 
                job_id, 
                input_path, 
                module_name, 
                module_id
            )
        )
        thread.daemon = True
        thread.start()
        
        return {
            'success': True,
            'message': 'Generation started',
            'job_id': job_id
        }

    except Exception as e:
        print(f"Error in trigger_learning_model_generation: {e}")
        return {'success': False, 'error': str(e)}


def run_learning_generation_task(app, job_id, image_path, module_name, module_id):
    """
    Background task for ComfyUI generation specific to learning modules.
    Uploads generated model to Supabase and updates the classroom_modules record.
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
                import shutil
                shutil.move(final_glb, dest_path)
                
                # Upload to Supabase Storage
                model_url = supabase_service.upload_file("models", dest_path, filename)
                print(f"✓ Uploaded Learning Model to Supabase: {model_url}")
                
                # Update classroom_modules record with the model_url
                if module_id:
                    try:
                        supabase_service.update_record(
                            'classroom_modules',
                            {'id': module_id},
                            {'model_url': model_url}
                        )
                        print(f"✓ Updated classroom_modules record {module_id} with model_url")
                    except Exception as e:
                        print(f"⚠️ Failed to update classroom_modules: {e}")
                        
            print(f"Learning generation job {job_id} complete")
                
        except Exception as e:
            print(f"Learning generation job {job_id} failed: {e}")
        finally:
            if os.path.exists(image_path):
                os.remove(image_path)


@learning_modules_bp.route('/api/create_module_with_generation', methods=['POST'])
def create_module_with_generation():
    """
    Create a new learning module with AI-generated 3D model.
    Steps:
    1. Upload Image to Supabase Storage (bucket: user_uploads).
    2. Extract text from PDF.
    3. Generate Quiz from text.
    4. Insert record into 'classroom_modules' table.
    5. Trigger 3D model generation (will update model_url when complete).
    """
    try:
        # 1. Validate Form Data
        module_name = request.form.get('module_name')
        module_desc = request.form.get('description', '')
        classroom_id = request.form.get('classroom_id')

        if not module_name:
            return jsonify({'error': 'module_name is required'}), 400

        # 2. Validate Files
        if 'image' not in request.files or 'pdf' not in request.files:
            return jsonify({'error': 'Missing files. Required: image, pdf'}), 400

        image_file = request.files['image']
        pdf_file = request.files['pdf']

        print(f"DEBUG: Processing files - Image: {image_file.filename}, PDF: {pdf_file.filename}")

        if image_file.filename == '' or pdf_file.filename == '':
            return jsonify({'error': 'One or more selected files have no filename'}), 400

        if not allowed_file(image_file.filename, ALLOWED_IMAGE_EXTENSIONS):
            return jsonify({'error': f'Invalid image file type: {image_file.filename}'}), 400
        if not allowed_file(pdf_file.filename, ALLOWED_PDF_EXTENSIONS):
            return jsonify({'error': 'Invalid PDF file type'}), 400

        # 3. Save files temporarily
        upload_id = str(uuid.uuid4())
        temp_dir = os.path.join(current_app.config.get('OUTPUT_DIR', 'temp_uploads'), upload_id)
        os.makedirs(temp_dir, exist_ok=True)

        image_filename = secure_filename(image_file.filename)
        pdf_filename = secure_filename(pdf_file.filename)

        temp_image_path = os.path.join(temp_dir, image_filename)
        temp_pdf_path = os.path.join(temp_dir, pdf_filename)

        image_file.save(temp_image_path)
        pdf_file.save(temp_pdf_path)

        # 4. Upload Image to Supabase Storage
        try:
            image_dest = f"{upload_id}/{image_filename}"
            image_url = supabase_service.upload_file("user_uploads", temp_image_path, image_dest)
        except Exception as e:
            return jsonify({'error': f"Failed to upload to storage: {str(e)}"}), 500

        # 5. Process PDF & Generate Quiz
        try:
            pdf_text = extract_text_from_file(temp_pdf_path)
            quiz_data = generate_quiz_from_text(pdf_text)
            summary_text = generate_summary_from_text(pdf_text)
        except Exception as e:
            return jsonify({'error': f"Failed to process content: {str(e)}"}), 500

        # 6. Insert into Database first (model_url will be updated later when generation completes)
        record = {
            "module_name": module_name,
            "module_desc": module_desc,
            "image_url": image_url,
            "model_url": None,  # Will be updated when generation completes
            "quiz": quiz_data,
            "summary": summary_text,
            "classroom_id": classroom_id if classroom_id else None
        }

        try:
            inserted_data = supabase_service.insert_record('classroom_modules', record)
            # Get the module_id from the inserted record
            module_id = inserted_data[0].get('id') if inserted_data and len(inserted_data) > 0 else None
        except Exception as e:
            return jsonify({'error': f"Database insertion failed: {str(e)}"}), 500

        # 7. Trigger 3D Model Generation from Image (pass module_id for callback)
        with open(temp_image_path, 'rb') as img_f:
            from io import BytesIO
            from werkzeug.datastructures import FileStorage
            img_bytes = BytesIO(img_f.read())
            img_for_gen = FileStorage(stream=img_bytes, filename=image_filename)
            generation_result = trigger_learning_model_generation(img_for_gen, module_name, module_id)

        if not generation_result.get('success'):
            # Generation failed to start, but record is already created
            print(f"⚠️ Model generation failed to start: {generation_result.get('error')}")
            
        job_id = generation_result.get('job_id')

        # 8. Cleanup temp files
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except:
            pass  # Non-critical

        return jsonify({
            "success": True,
            "message": "Module created successfully. 3D model generation is in progress.",
            "module_id": module_id,
            "job_id": job_id,
            "data": record
        }), 201

    except Exception as e:
        return jsonify({'error': f"Server error: {str(e)}"}), 500
