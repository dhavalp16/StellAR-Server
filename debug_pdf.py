
import sys
import os
from pdf2image import convert_from_path, pdfinfo_from_path

print(f"Python executable: {sys.executable}")
print(f"PATH env: {os.environ.get('PATH')}")

pdf_path = 'samples/lech101.pdf'

if not os.path.exists(pdf_path):
    print(f"Error: {pdf_path} does not exist.")
    sys.exit(1)

try:
    print(f"\nAttempting to read info for {pdf_path}...")
    info = pdfinfo_from_path(pdf_path)
    print("PDF Info:")
    print(info)
    
    print(f"\nAttempting to convert {pdf_path}...")
    images = convert_from_path(pdf_path, first_page=1, last_page=1)
    print(f"Successfully converted first page. Image object: {images[0]}")
    
except Exception as e:
    print(f"\nERROR OCCURRED:")
    print(e)
    # import traceback
    # traceback.print_exc()
