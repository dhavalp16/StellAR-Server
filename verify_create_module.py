
import os
import sys
import io
from flask import Flask
from unittest.mock import MagicMock

# Ensure modules can be imported
sys.path.append(os.getcwd())

# Mock Supabase Service BEFORE importing modules
sys.modules['modules.supabase_service'] = MagicMock()
mock_service = MagicMock()
sys.modules['modules.supabase_service'].supabase_service = mock_service

# Mock OCR and Quiz Generator
sys.modules['modules.api.ocr'] = MagicMock()
sys.modules['modules.api.ocr'].extract_text_from_file.return_value = "Mock PDF text content."

sys.modules['modules.quiz_generator'] = MagicMock()
sys.modules['modules.quiz_generator'].generate_quiz_from_text.return_value = [{"question": "Q1?", "options": ["A"], "correct_answer": "A"}]

# Mock upload_file to return dummy URLs
mock_service.upload_file.side_effect = lambda bucket, source, dest: f"https://mock.supabase.co/{bucket}/{dest}"
mock_service.insert_record.return_value = {"id": 1}

try:
    from modules.api.learning_modules import learning_modules_bp
    print("Successfully imported learning_modules_bp")
    
    app = Flask(__name__)
    app.config['OUTPUT_DIR'] = 'temp_test'
    app.register_blueprint(learning_modules_bp)
    
    client = app.test_client()
    
    # Create dummy files
    data = {
        'module_name': 'Test Module',
        'description': 'Test Description',
        'classroom_id': '123e4567-e89b-12d3-a456-426614174000',
        'image': (io.BytesIO(b"fake image data"), 'test.jpg'),
        'model': (io.BytesIO(b"fake model data"), 'test.glb'),
        'pdf': (io.BytesIO(b"fake pdf data"), 'test.pdf')
    }
    
    print("Sending request to /api/create_module...")
    response = client.post('/api/create_module', data=data, content_type='multipart/form-data')
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json}")
    
    if response.status_code == 201:
        print("PASS: Module creation flow succeeded (mocked).")
    else:
        print("FAIL: Request failed.")

except Exception as e:
    print(f"An error occurred: {e}")
    import traceback
    traceback.print_exc()
