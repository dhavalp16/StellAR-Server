
import os
import sys

# Ensure modules can be imported
sys.path.append(os.getcwd())

try:
    from modules.api.ocr import extract_text_from_file
    print("Successfully imported extract_text_from_file")
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)

# Test file path
test_file = "samples/lech101.pdf"

if not os.path.exists(test_file):
    print(f"Test file not found: {test_file}")
    sys.exit(1)

print(f"Testing extraction on {test_file}...")
try:
    text = extract_text_from_file(test_file)
    print("Extraction successful!")
    print("-" * 20)
    print(text[:200]) # Print first 200 chars
    print("-" * 20)
    
    if len(text.strip()) > 0:
        print("PASS: Text was extracted.")
    else:
        print("FAIL: No text extracted.")
        
except Exception as e:
    print(f"An error occurred: {e}")
