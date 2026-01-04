
import pytesseract
from PIL import Image
try:
    print("Testing Tesseract...")
    text = pytesseract.image_to_string(Image.open('samples/lech101.pdf'))
    print(f"Extracted ({len(text)} chars):")
    print(text)
except Exception as e:
    print(f"Error: {e}")
