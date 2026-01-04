
import os
import sys
from unittest.mock import MagicMock, patch

# Ensure modules can be imported
sys.path.append(os.getcwd())

# Mock pytesseract and pdf2image BEFORE importing modules that use them
sys.modules['pytesseract'] = MagicMock()
sys.modules['pdf2image'] = MagicMock()
sys.modules['PIL'] = MagicMock()

# Setup the mock return values
sys.modules['pytesseract'].Output.DICT = 'dict'
sys.modules['pytesseract'].image_to_data.return_value = {
    'text': ['Hello', 'World', ''],
    'conf': [90, 85, 0],
    'left': [0, 10, 20],
    'top': [0, 0, 0],
    'width': [10, 10, 0],
    'height': [10, 10, 0]
}

# Mock Image.open to return a dummy object
mock_image = MagicMock()
sys.modules['PIL'].Image.open.return_value = mock_image

try:
    from modules.api.ocr import extract_text_from_file
    print("Successfully imported extract_text_from_file")
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)

# Test file path
test_file = "samples/Venus.jpg"

# We don't really need the file to exist for the mock test, 
# but the function checks for file extension, so usage is:
try:
    print(f"Testing extraction on {test_file} with MOCKS...")
    text = extract_text_from_file(test_file)
    print("Extraction successful (mocked)!")
    print("-" * 20)
    print(f"Extracted Text: {text}")
    print("-" * 20)
    
    if "Hello World" in text:
        print("PASS: Expected text found.")
    else:
        print(f"FAIL: Unexpected text: {text}")
        
except Exception as e:
    print(f"An error occurred: {e}")
