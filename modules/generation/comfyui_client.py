import requests
import json
import time
import glob
import os
import uuid

class ComfyUIClient:
    def __init__(self, comfyui_url="http://127.0.0.1:8188"):
        self.comfyui_url = comfyui_url
        self.client_id = str(uuid.uuid4())
        self.check_connection()
    
    def check_connection(self):
        """Check if ComfyUI server is accessible"""
        try:
            response = requests.get(f"{self.comfyui_url}")
            if response.status_code == 200:
                print("✓ ComfyUI server is accessible")
            else:
                print(f"✗ ComfyUI server returned status: {response.status_code}")
        except Exception as e:
            print(f"✗ Cannot connect to ComfyUI server: {e}")
    
    def queue_prompt(self, workflow):
        """Queue a prompt in ComfyUI"""
        p = {"prompt": workflow, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        headers = {'Content-Type': 'application/json'}
        
        try:
            resp = requests.post(f"{self.comfyui_url}/prompt", data=data, headers=headers)
            if resp.status_code == 200:
                result = resp.json()
                print(f"✓ Prompt queued successfully (ID: {result.get('prompt_id', 'Unknown')})")
                return result
            else:
                print(f"✗ Failed to queue prompt: {resp.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to queue prompt: {e}")
            return None
    
    def upload_image(self, image_path):
        """Upload image to ComfyUI"""
        try:
            with open(image_path, 'rb') as f:
                upload_resp = requests.post(f"{self.comfyui_url}/upload/image", files={'image': f})
                if upload_resp.status_code == 200:
                    result = upload_resp.json()
                    print(f"✓ Image uploaded successfully: {result['name']}")
                    return result['name']
                else:
                    print(f"✗ Image upload failed: {upload_resp.status_code}")
                    return None
        except Exception as e:
            print(f"✗ Image upload error: {e}")
            return None
    
    def wait_for_completion(self, target_file_pattern, timeout=600):
        """Wait for ComfyUI to generate the file"""
        print(f"Waiting for file generation: {target_file_pattern}")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            files = glob.glob(target_file_pattern)
            
            if files:
                file_path = files[0]
                print(f"✓ File found: {os.path.basename(file_path)}")
                
                # Wait for file to be completely written
                prev_size = -1
                stable_count = 0
                
                while stable_count < 3:  # 3 consecutive stable readings
                    try:
                        curr_size = os.path.getsize(file_path)
                        if curr_size == prev_size and curr_size > 0:
                            stable_count += 1
                        else:
                            stable_count = 0
                        prev_size = curr_size
                        time.sleep(1)
                    except OSError:
                        time.sleep(1)
                        continue
                
                print(f"✓ File generation completed: {os.path.basename(file_path)}")
                return file_path
            
            # Show progress
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0:
                print(f"Waiting... {elapsed}s elapsed")
            
            time.sleep(2)
        
        print(f"✗ File generation timeout after {timeout} seconds")
        return None