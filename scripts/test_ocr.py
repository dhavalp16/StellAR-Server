import requests
import os

# Configuration
BASE_URL = "http://localhost:5000/api/ocr"
IMAGE_PATH = "test_image.png"

def test_ocr():
    if not os.path.exists(IMAGE_PATH):
        print(f"❌ Error: {IMAGE_PATH} not found in current directory.")
        return

    print(f"🚀 Sending {IMAGE_PATH} to {BASE_URL}...")
    
    try:
        with open(IMAGE_PATH, 'rb') as f:
            files = {'file': f}
            response = requests.post(BASE_URL, files=files)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Success!")
            print(f"📄 Extracted Text:\n{'-'*20}")
            print(data.get('text', 'No text found'))
            print(f"{'-'*20}")
            print(f"📊 Word Count: {data.get('count', 0)}")
            print(f"🔑 Keywords: {data.get('keywords', [])}")
        else:
            print(f"\n❌ Failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")

if __name__ == "__main__":
    test_ocr()
