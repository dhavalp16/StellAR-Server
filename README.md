# 🪐 CosmicLens: AI Planet Detection & 3D Generation

**CosmicLens** is an intelligent web application that detects planets in 2D images and transforms them into interactive 3D models. Powered by **YOLOv8** for detection and **ComfyUI (Hunyuan3D)** for generation.

![Project Banner](https://via.placeholder.com/1200x400?text=CosmicLens+AI+Demo)

## ✨ Features

*   **🔍 Multi-Planet Detection**: Automatically identifies and classifies planets (Earth, Mars, Jupiter, etc.) in any image.
*   **🧊 2D to 3D Conversion**: Generates high-quality `.glb` 3D models from 2D planetary images.
*   **🌍 Interactive Viewer**: Inspect generated models in a real-time Three.js 3D viewer.
*   **🚀 GPU Accelerated**: Optimized for NVIDIA GPUs (CUDA) for fast inference and generation.

## 🛠️ Tech Stack

*   **Backend**: Python, Flask
*   **AI/ML**: YOLOv8 (Ultralytics), PyTorch
*   **Generation**: ComfyUI, Hunyuan3D
*   **Frontend**: HTML5, CSS3, JavaScript, Three.js

## 📂 Project Structure

```
├── app.py                 # Main Flask application
├── dataset/               # Training data (Images & Labels)
├── models/                # Trained models & generated 3D assets
├── modules/               # Core logic (Detection & Generation)
├── scripts/               # Utility scripts (Train, Test, Preprocess)
├── samples/               # Sample images for testing
├── templates/             # Web UI templates
└── workflows/             # ComfyUI workflow configurations
```

## 🚀 Getting Started

### Prerequisites

*   Python 3.10+
*   NVIDIA GPU (Recommended)
*   [ComfyUI](https://github.com/comfyanonymous/ComfyUI) running locally on port `8188`.

### Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/cosmic-lens.git
    cd cosmic-lens
    ```

2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Setup ComfyUI**
    *   Ensure ComfyUI is running.
    *   Install the Hunyuan3D nodes/workflows.

### Usage

1.  **Start the Server**
    ```bash
    python app.py
    ```

2.  **Open Web Interface**
    *   Navigate to `http://localhost:5000` in your browser.

3.  **Detect & Generate**
    *   Upload an image of a planet.
    *   Click **Detect** to find planets.
    *   Select a planet and click **Generate 3D** to create a model.

## 🔌 API Documentation

The server exposes a RESTful API for the mobile client.

### Authentication
*   **Register**: `POST /api/auth/register` (`username`, `password`)
*   **Login**: `POST /api/auth/login` (`username`, `password`) -> Returns `access_token`

### Core Features
*   **Scan Image**: `POST /api/scan` (Header: `Authorization: Bearer <token>`)
    *   Uploads image, detects planets, returns metadata.
*   **List Models**: `GET /api/models`
    *   Returns list of available 3D models.
*   **Generate 3D**: `POST /api/models/generate`
    *   Triggers background generation task.

## 🧠 Training the Model

To retrain the YOLOv8 detection model:

```bash
python scripts/train.py
```

To evaluate the model:

```bash
python scripts/evaluate.py
```

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
