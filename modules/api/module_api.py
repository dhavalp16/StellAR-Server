from flask import Blueprint, request, jsonify, current_app
import os
import uuid
import ollama
from werkzeug.utils import secure_filename

from modules.api.ocr import extract_text_from_file
from modules.quiz_generator import generate_quiz_from_text, generate_summary_from_text

module_api_bp = Blueprint('module_api', __name__, url_prefix='/api/module')

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'webp'}


def allowed_file(filename, allowed_extensions):
    """Check if the file has an allowed extension."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower().strip()
    return ext in allowed_extensions


@module_api_bp.route('/process', methods=['POST'])
def process_content():
    """
    Process a PDF file and/or text to generate a summary and quiz.
    
    Accepts:
        - 'pdf' (file, optional): A PDF file to extract text from
        - 'text' (form field, optional): Additional text content
        
    At least one of 'pdf' or 'text' must be provided.
    
    Returns:
        JSON with:
        - extracted_text: Text extracted from PDF (if provided)
        - combined_text: All text combined (PDF + provided text)
        - summary: AI-generated summary of the content
        - quiz: List of 10 multiple-choice questions
    """
    try:
        extracted_text = ""
        provided_text = ""
        temp_path = None
        
        print("DEBUG: Received request with data:", request.form)
        print("DEBUG: Request files:", request.files)
        
        # Get text from form data
        try:
            provided_text = request.form.get('description', '').strip()
            print(f"DEBUG: Got provided_text = '{provided_text}'")
        except Exception as e:
            print(f"DEBUG: Error getting description: {e}")
            provided_text = ""
        
        # Process PDF if provided
        if 'file' in request.files:
            pdf_file = request.files['file']
            
            if pdf_file.filename != '':
                print(f"DEBUG: Checking file: '{pdf_file.filename}'")
                
                # Check if file has an extension
                if '.' not in pdf_file.filename:
                    print(f"DEBUG: File has no extension!")
                    return jsonify({
                        'error': f'File has no extension. Please upload a file with one of these extensions: {", ".join(ALLOWED_EXTENSIONS)}'
                    }), 400
                
                file_ext = pdf_file.filename.rsplit('.', 1)[1].lower().strip()
                print(f"DEBUG: File extension: '{file_ext}'")
                
                if not allowed_file(pdf_file.filename, ALLOWED_EXTENSIONS):
                    return jsonify({
                        'error': f'Invalid file type "{file_ext}". Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
                    }), 400
                
                # Save file temporarily
                file_id = str(uuid.uuid4())
                output_dir = current_app.config.get('OUTPUT_DIR', 'temp_uploads')
                os.makedirs(output_dir, exist_ok=True)
                
                ext = os.path.splitext(pdf_file.filename)[1].lower()
                temp_filename = secure_filename(f"temp_module_{file_id}{ext}")
                temp_path = os.path.join(output_dir, temp_filename)
                pdf_file.save(temp_path)
                
                print(f"DEBUG: Processing file - {pdf_file.filename}")
                
                # Extract text from PDF
                extracted_text = extract_text_from_file(temp_path)
                print(f"DEBUG: Extracted {len(extracted_text)} characters from PDF")
        
        # Combine texts
        combined_text = ""
        if extracted_text:
            combined_text += extracted_text
        if provided_text:
            if combined_text:
                combined_text += "\n\n" + provided_text
            else:
                combined_text = provided_text
        
        # Validate we have content to process
        print(f"DEBUG: extracted_text = '{extracted_text}'")
        print(f"DEBUG: provided_text = '{provided_text}'")
        print(f"DEBUG: combined_text = '{combined_text}'")
        print(f"DEBUG: combined_text.strip() = '{combined_text.strip()}'")
        print(f"DEBUG: bool(combined_text.strip()) = {bool(combined_text.strip())}")
        
        if not combined_text.strip():
            print("DEBUG: Validation failed - no content")
            return jsonify({
                'error': 'No content provided. Please provide a PDF file or text.'
            }), 400
        
        print("DEBUG: Validation passed - proceeding with processing")
        
        print(f"DEBUG: Combined text length: {len(combined_text)} characters")
        
        # Generate summary
        print("DEBUG: Generating summary...")
        summary = generate_summary_from_text(combined_text)
        print(f"DEBUG: Summary generated: {len(summary)} characters")
        
        # Generate quiz (10 questions)
        print("DEBUG: Generating quiz...")
        quiz = generate_quiz_from_text(combined_text)
        print(f"DEBUG: Quiz generated: {len(quiz)} questions")
        print(f"DEBUG: Quiz: {quiz}")
        
        response_data = {
            "success": True,
            "summary": summary,
            "quiz": quiz,
            "quiz_count": len(quiz),
            "extracted_text": combined_text  # For chatbot context
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"ERROR in process_content: {str(e)}")
        return jsonify({'error': f"Server error: {str(e)}"}), 500
        
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
            print(f"DEBUG: Cleaned up temp file: {temp_path}")


@module_api_bp.route('/quiz', methods=['POST'])
def generate_quiz_only():
    """
    Generate a quiz from provided text only (no PDF upload).
    
    Accepts:
        - 'text' (JSON body): Text content to generate quiz from
        
    Returns:
        JSON with:
        - quiz: List of 10 multiple-choice questions
    """
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing "text" field in request body'}), 400
        
        text = data['text'].strip()
        
        if not text:
            return jsonify({'error': 'Text content is empty'}), 400
        
        print(f"DEBUG: Generating quiz from {len(text)} characters")
        
        quiz = generate_quiz_from_text(text)
        
        return jsonify({
            "success": True,
            "quiz": quiz,
            "quiz_count": len(quiz)
        }), 200
        
    except Exception as e:
        print(f"ERROR in generate_quiz_only: {str(e)}")
        return jsonify({'error': f"Server error: {str(e)}"}), 500


@module_api_bp.route('/summary', methods=['POST'])
def generate_summary_only():
    """
    Generate a summary from provided text only (no PDF upload).
    
    Accepts:
        - 'text' (JSON body): Text content to generate summary from
        
    Returns:
        JSON with:
        - summary: AI-generated summary of the content
    """
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing "text" field in request body'}), 400
        
        text = data['text'].strip()
        
        if not text:
            return jsonify({'error': 'Text content is empty'}), 400
        
        print(f"DEBUG: Generating summary from {len(text)} characters")
        
        summary = generate_summary_from_text(text)
        
        return jsonify({
            "success": True,
            "summary": summary
        }), 200
        
    except Exception as e:
        print(f"ERROR in generate_summary_only: {str(e)}")
        return jsonify({'error': f"Server error: {str(e)}"}), 500


# ================================
# CHATBOT ENDPOINTS
# ================================

def generate_chat_response(context: str, message: str, history: list = None) -> str:
    """
    Generate a chatbot response using Ollama.
    
    Args:
        context: Document text to answer questions about
        message: User's current question
        history: Optional list of previous conversation turns
    
    Returns:
        AI-generated response string
    """
    # Build conversation history string
    history_text = ""
    if history:
        for turn in history:
            role = turn.get('role', 'user')
            content = turn.get('content', '')
            if role == 'user':
                history_text += f"User: {content}\n"
            else:
                history_text += f"Assistant: {content}\n"
    
    # Build history section
    history_section = ""
    if history_text:
        history_section = f"CONVERSATION HISTORY:\n{history_text}"
    
    # Build the prompt
    prompt = f"""You are a helpful educational assistant answering questions about a document.

DOCUMENT CONTENT:
{context}

{history_section}

USER QUESTION: {message}

Instructions:
- Answer based ONLY on the document content provided above.
- If the information is not in the document, clearly say "This information is not in the provided document."
- Be concise and educational in your responses.
- If relevant, quote specific parts from the document."""

    try:
        response = ollama.chat(
            model='phi3:mini',
            messages=[
                {
                    'role': 'user',
                    'content': prompt,
                }
            ]
        )
        return response['message']['content']
    except Exception as e:
        print(f"ERROR in generate_chat_response: {str(e)}")
        raise e


@module_api_bp.route('/chat', methods=['POST'])
def chat_with_document():
    """
    Chat with a document using AI.
    
    Accepts (JSON body):
        - 'context' (required): The document text to answer questions about
        - 'message' (required): The user's question
        - 'history' (optional): List of previous conversation turns
          Each turn: {"role": "user"|"assistant", "content": "..."}
    
    Returns:
        JSON with:
        - response: AI-generated answer
        - role: "assistant"
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
        
        # Validate required fields
        if 'context' not in data:
            return jsonify({'error': 'Missing "context" field - provide the document text'}), 400
        
        if 'message' not in data:
            return jsonify({'error': 'Missing "message" field - provide your question'}), 400
        
        context = data['context'].strip()
        message = data['message'].strip()
        history = data.get('history', [])
        
        if not context:
            return jsonify({'error': 'Context cannot be empty'}), 400
        
        if not message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        print(f"DEBUG: Chat request - context: {len(context)} chars, message: {message[:50]}...")
        
        # Generate response
        response_text = generate_chat_response(context, message, history)
        
        print(f"DEBUG: Chat response generated: {len(response_text)} chars")
        
        return jsonify({
            "success": True,
            "response": response_text,
            "role": "assistant"
        }), 200
        
    except Exception as e:
        print(f"ERROR in chat_with_document: {str(e)}")
        return jsonify({'error': f"Server error: {str(e)}"}), 500
