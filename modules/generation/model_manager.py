import os
import json

class ModelManager:
    def __init__(self, models_dir="generated_models"):
        self.models_dir = models_dir
        os.makedirs(models_dir, exist_ok=True)
    
    def save_model_info(self, model_name, model_data):
        """Save model metadata"""
        info_path = os.path.join(self.models_dir, f"{model_name}_info.json")
        with open(info_path, 'w') as f:
            json.dump(model_data, f, indent=2)
    
    def load_model_info(self, model_name):
        """Load model metadata"""
        info_path = os.path.join(self.models_dir, f"{model_name}_info.json")
        if os.path.exists(info_path):
            with open(info_path, 'r') as f:
                return json.load(f)
        return None
    
    def list_models(self):
        """List all available models"""
        models = []
        for file in os.listdir(self.models_dir):
            if file.endswith('.glb'):
                model_path = os.path.join(self.models_dir, file)
                info_path = os.path.join(self.models_dir, f"{os.path.splitext(file)[0]}_info.json")
                
                model_data = {
                    'name': file,
                    'size': os.path.getsize(model_path),
                    'created': os.path.getctime(model_path)
                }
                
                if os.path.exists(info_path):
                    with open(info_path, 'r') as f:
                        model_data['info'] = json.load(f)
                
                models.append(model_data)
        
        return models