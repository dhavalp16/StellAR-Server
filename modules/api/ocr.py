from flask import Blueprint, request, jsonify, current_app
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import os
import uuid
import re
from collections import Counter

# -------------------------------
# Stop words
# -------------------------------
STOP_WORDS = {
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for',
    'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his',
    'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my',
    'one', 'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 'if',
    'about', 'who', 'get', 'which', 'go', 'me', 'is', 'are', 'was', 'were',
    'has', 'had', 'been', 'can', 'could', 'should', 'may', 'might', 'must',
    'shall', 'some', 'any', 'no', 'only', 'own', 'same', 'than', 'too', 'very',
    'just', 'where', 'when', 'why', 'how', 'here', 'image', 'text'
}

# -------------------------------
# Keyword Extraction Logic
# -------------------------------
def extract_keywords(text, num_keywords=3):
    if not text:
        return []

    original_words = re.findall(r'\b[A-Za-z]+\b', text)
    clean_text = re.sub(r'[^a-zA-Z\s]', '', text.lower())
    words = clean_text.split()

    scores = Counter()

    for idx, word in enumerate(words):
        if word in STOP_WORDS or len(word) < 3:
            continue

        score = 1

        # Topic bias (early words)
        if idx < 20:
            score += 3

        # Proper noun boost
        for ow in original_words:
            if ow.lower() == word and ow[0].isupper():
                score += 4
                break

        scores[word] += score

    return [word for word, _ in scores.most_common(num_keywords)]


# -------------------------------
# OCR Processing Logic
# -------------------------------
def process_ocr(file_path):
    """
    Process an image or PDF file and return extracted text and word details.
    
    Args:
        file_path (str): Path to the image or PDF file.
        
    Returns:
        dict: Contains 'text' (str) and 'words' (list).
    """
    ext = os.path.splitext(file_path)[1].lower()
    images = []

    # -------------------------------
    # Handle PDF
    # -------------------------------
    if ext == '.pdf':
        images = convert_from_path(file_path, dpi=300)

    # -------------------------------
    # Handle Image
    # -------------------------------
    else:
        images = [Image.open(file_path)]

    words = []
    full_text = []

    # -------------------------------
    # OCR each page
    # -------------------------------
    for page_num, image in enumerate(images):
        ocr_data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT
        )

        for i in range(len(ocr_data['text'])):
            text = ocr_data['text'][i].strip()
            conf = int(ocr_data['conf'][i])

            if text and conf > 50:
                words.append({
                    "text": text,
                    "confidence": conf,
                    "page": page_num + 1,
                    "bbox": {
                        "x": ocr_data['left'][i],
                        "y": ocr_data['top'][i],
                        "w": ocr_data['width'][i],
                        "h": ocr_data['height'][i]
                    }
                })
                full_text.append(text)

    joined_text = " ".join(full_text)
    
    return {
        "text": joined_text,
        "words": words
    }

def extract_text_from_file(file_path):
    """
    Extract text content from a file (image or PDF).
    
    Args:
        file_path (str): Path to the file.
        
    Returns:
        str: extracted text.
    """
    result = process_ocr(file_path)
    return result['text']

# -------------------------------
# Blueprint
# -------------------------------
ocr_bp = Blueprint('ocr', __name__, url_prefix='/api/ocr')

@ocr_bp.route('', methods=['POST'])
def scan_text():
    """
    Upload image or PDF -> OCR -> extract text, bounding boxes, keywords
    """

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    temp_id = str(uuid.uuid4())
    output_dir = current_app.config.get('OUTPUT_DIR', 'temp_uploads')
    os.makedirs(output_dir, exist_ok=True)

    ext = os.path.splitext(file.filename)[1].lower()
    temp_path = os.path.join(output_dir, f"temp_ocr_{temp_id}{ext}")
    file.save(temp_path)

    try:
        ocr_result = process_ocr(temp_path)
        keywords = extract_keywords(ocr_result['text'])

        return jsonify({
            "success": True,
            "text": ocr_result['text'],
            "count": len(ocr_result['words']),
            "keywords": keywords,
            "words": ocr_result['words']
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

