
import os
import sys
from modules.api.ocr import extract_text_from_file

# Ensure modules can be imported
sys.path.append(os.getcwd())

pdf_path = 'samples/lech101.pdf'

if not os.path.exists(pdf_path):
    print(f"File not found: {pdf_path}")
    sys.exit(1)

print(f"Extracting text from {pdf_path}...")
try:
    text = extract_text_from_file(pdf_path)
    length = len(text)
    print(f"Extraction complete.")
    print(f"Total characters: {length}")
    print("-" * 20)
    print("First 500 characters:")
    print(text[:500])
    print("-" * 20)
    
    if length > 1000:
        print("PASS: Extracted a significant amount of text.")
    else:
        print("WARNING: Extracted text seems short for a 10-page PDF.")

except Exception as e:
    print(f"Error: {e}")
