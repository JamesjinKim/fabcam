# fabcam

Raspberry Pi 4 CCTV System - 오프라인 환경에서 동작하는 간단한 CCTV 시스템

## Project Structure

```
fabcam/
├── backend/
│   ├── main.py              # FastAPI 서버
│   ├── camera.py            # 카메라 관리
│   └── models.py            # 데이터 모델
├── frontend/
│   ├── index.html           # 메인 UI
│   ├── style.css           # 스타일
│   └── script.js           # JavaScript 로직
├── static/
│   ├── videos/             # 녹화된 비디오
│   └── images/             # 스냅샷 이미지
├── requirements.txt        # Python 의존성
├── start.sh               # 시작 스크립트
└── README.md              # 프로젝트 문서
```

## Development

### Setup
```bash
# Clone the repository
git clone https://github.com/JamesjinKim/fabcam.git
cd fabcam

# Install Python dependencies
pip install -r requirements.txt

# Create storage directories
mkdir -p static/videos static/images
```

### Commands
```bash
# Start the server
./start.sh

# Or manually:
cd backend && python main.py

# The server will be available at http://localhost:8000
```

### Tech Stack
- **Backend**: Python 3, FastAPI, OpenCV
- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Server**: Uvicorn
- **Storage**: Local filesystem

## Features

- 📹 실시간 비디오 스트리밍 (MJPEG)
- 🎬 비디오 녹화 시작/정지
- 📸 스냅샷 캡처
- 📁 파일 관리 (목록, 다운로드, 삭제)
- 📱 반응형 웹 UI (PC/모바일 지원)
- 🔌 오프라인 동작

## API Endpoints

- `GET /` - 메인 웹 UI
- `GET /video_feed` - MJPEG 비디오 스트림
- `POST /api/recording/start` - 녹화 시작
- `POST /api/recording/stop` - 녹화 정지
- `GET /api/recording/status` - 녹화 상태 확인
- `POST /api/snapshot` - 스냅샷 캡처
- `GET /api/files` - 저장된 파일 목록
- `GET /api/files/{type}/{filename}` - 파일 다운로드
- `DELETE /api/files/{type}/{filename}` - 파일 삭제

## Keyboard Shortcuts

- `Ctrl+R`: 녹화 시작/정지
- `Ctrl+S`: 스냅샷 캡처
- `Ctrl+L`: 파일 목록 새로고침

## Notes

- Raspberry Pi Camera Module 또는 USB 카메라 지원
- 라즈베리파이 로컬 네트워크에서만 동작
- 인터넷 연결 불필요
- 모든 데이터는 로컬에 저장