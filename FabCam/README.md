# Fabcam - Raspberry Pi 4 CCTV System

A simple offline CCTV system built with Raspberry Pi 4 and camera module.

## Features

- Real-time video streaming via MJPEG
- Video recording and snapshot capture
- File management and download
- Web-based UI
- Offline operation

## Tech Stack

- **Backend**: Python 3, FastAPI
- **Video Processing**: OpenCV
- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Web Server**: Uvicorn
- **Storage**: Local filesystem

## Setup

### 🚀 UV 방식 (권장 - 4배 빠름)

1. UV 환경 설정 (한 번만):
```bash
./setup-uv.sh
```

2. 서버 시작:
```bash
./start-uv.sh
```

### 📦 기존 pip 방식

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
cd backend
python main.py
```

### 🌐 접속

브라우저에서 `http://localhost:8000` 접속

## Project Structure

```
fabcam/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── camera.py            # Camera handling
│   └── models.py            # Data models
├── frontend/
│   ├── index.html           # Main UI
│   ├── style.css           # Styles
│   └── script.js           # JavaScript logic
├── static/
│   ├── videos/             # Recorded videos
│   └── images/             # Captured images
└── requirements.txt        # Dependencies
```