# AI Interview Trainer

> **Version 1 — Real-Time Face Detection Pipeline**  
> A production-quality, modular computer-vision system built with Python 3.10+ and OpenCV.

---

## Overview

This project is a real-time video processing pipeline designed as the foundation for a full AI Interview Trainer. V1 detects faces via a Haar Cascade classifier and overlays live feedback on the webcam stream. The architecture is explicitly designed to be extended with emotion recognition, pose estimation, and NLP analysis in future versions.

---

## Project Structure

```
ai-interview-trainer/
├── backend/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                        # Pipeline entry point
│   │   ├── preprocessing/
│   │   │   ├── __init__.py
│   │   │   └── video_capture.py           # Webcam abstraction
│   │   ├── cv_models/
│   │   │   ├── __init__.py
│   │   │   └── face_detection.py          # Haar Cascade face detector
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── config.py                  # All tunable parameters
│   │       └── logger.py                  # Structured rotating-file logger
│   ├── logs/                              # Auto-created at runtime
│   └── requirements.txt
├── frontend/
└── README.md
```

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python      | ≥ 3.10  |
| pip         | ≥ 23.x  |
| Webcam      | Any USB / built-in |

---

## Setup

### 1 — Clone the repository

```bash
git clone https://github.com/<your-username>/ai-interview-trainer.git
cd ai-interview-trainer
```

### 2 — Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

### 3 — Install dependencies

```bash
pip install -r backend/requirements.txt
```

---

## Running

```bash
cd backend
python -m src.main
```

The application opens a window titled **AI Interview Trainer — Real-Time Face Detection**.

| Action | Behaviour |
|--------|-----------|
| Face in frame | Green bounding box + "Face Detected (N)" |
| No face | Red status text "No Face Detected" |
| Press `q` | Clean shutdown |
| `Ctrl-C` | Graceful interrupt |

---

## Configuration

All parameters live in `backend/src/utils/config.py`. No magic numbers anywhere else.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `camera.index` | `0` | Device index passed to `cv2.VideoCapture` |
| `camera.frame_width` | `1280` | Requested capture width (px) |
| `camera.frame_height` | `720` | Requested capture height (px) |
| `camera.fps` | `30` | Requested frames per second |
| `face_detection.scale_factor` | `1.1` | Image pyramid reduction ratio |
| `face_detection.min_neighbors` | `5` | Minimum neighbours per detection |
| `face_detection.min_size` | `(80, 80)` | Minimum face size to detect |
| `display.quit_key` | `q` | Key that exits the application |

---

## Logging

Structured logs are written to both stdout and `logs/app.log` (auto-created). The file handler rotates at 5 MB and keeps 3 backups.

---

## Architecture — Design for Extensibility

```
VideoCapture  ──►  FaceDetector  ──►  Overlay Renderer  ──►  cv2.imshow
     │                   │
  CameraConfig    FaceDetectionConfig          AppConfig (root)
```

| Future module | Where to add |
|---------------|-------------|
| Emotion recognition | `backend/src/cv_models/emotion_detection.py` |
| Pose estimation | `backend/src/cv_models/pose_estimation.py` |
| Eye-contact analysis | `backend/src/cv_models/gaze_tracking.py` |
| NLP / speech | `backend/src/nlp/` |
| Web dashboard | `backend/src/api/` |

Each new model receives its own config slice from `AppConfig` and plugs into the pipeline loop in `backend/src/main.py` with zero changes to existing modules.

---

## License

MIT — see `LICENSE` for details.
