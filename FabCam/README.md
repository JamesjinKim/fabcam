# Fabcam - Raspberry Pi CCTV System

🎥 **Raspberry Pi Camera 지원 CCTV 시스템** - 오프라인에서 동작하는 스마트 감시 시스템

## ✨ 주요 기능

- 📹 **실시간 비디오 스트리밍** (MJPEG)
- 🎬 **비디오 녹화** 및 스냅샷 캡처
- 📁 **파일 관리** (목록, 다운로드, 삭제)
- 📱 **반응형 웹 UI** (PC/모바일 지원)
- 🔌 **완전 오프라인** 동작
- 🎥 **Raspberry Pi Camera** 및 USB 카메라 지원
- 🔄 **동적 카메라 전환** 지원

## 🛠️ 기술 스택

- **Backend**: Python 3.11+, FastAPI, rpicam-apps
- **Camera**: Raspberry Pi Camera (libcamera), OpenCV
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Server**: Uvicorn ASGI
- **Package Manager**: UV (빠른 Python 패키지 관리)
- **Storage**: 로컬 파일시스템

## 🚀 빠른 시작

### 원클릭 실행 (권장)

```bash
# 모든 것을 자동으로 설정하고 실행
./fabcam.sh
```

이 스크립트는 자동으로:
- ✅ UV 설치 확인 및 설치
- ✅ 가상환경 생성 및 활성화
- ✅ 의존성 자동 설치
- ✅ 카메라 자동 감지 (Pi Camera/USB)
- ✅ 적절한 백엔드 선택
- ✅ 서버 시작

### 수동 설정

```bash
# 1. 초기 설정
./uv-setup.sh

# 2. 서버 시작
./start-uv.sh
```

### 접속

- **로컬**: http://localhost:8000
- **네트워크**: http://[라즈베리파이_IP]:8000

## 📁 프로젝트 구조

```
FabCam/
├── fabcam.sh               # 🚀 원클릭 실행 스크립트
├── backend/
│   ├── main_auto.py        # 🎯 자동 카메라 감지 서버
│   ├── camera.py           # 📷 OpenCV 카메라 매니저
│   ├── pi_camera.py        # 🎥 Raspberry Pi 카메라 매니저
│   ├── camera_factory.py   # 🏭 카메라 자동 선택
│   └── models.py           # 📋 데이터 모델
├── frontend/
│   ├── index.html          # 🖥️ 메인 UI
│   ├── style.css          # 🎨 스타일
│   └── script.js          # ⚡ JavaScript 로직
├── static/
│   ├── videos/            # 🎬 녹화된 비디오
│   └── images/            # 📸 캡처된 이미지
├── pyproject.toml         # 📦 프로젝트 설정
└── .gitignore            # 🚫 Git 제외 파일
```

## 🎥 카메라 지원

### Raspberry Pi Camera (권장)
- **OV5647** 카메라 모듈 지원
- **libcamera/rpicam** 기반 고성능
- **다중 카메라** 지원 (CSI 포트 2개)
- 해상도: 640x480 ~ 2592x1944

### USB/웹캠
- **OpenCV** 기반 호환성
- **V4L2** 지원 카메라
- 자동 fallback 지원

## 🔧 API 엔드포인트

### 기본 API
- `GET /` - 메인 웹 UI
- `GET /video_feed` - MJPEG 비디오 스트림
- `GET /api/camera/info` - 카메라 정보

### 녹화/캡처
- `POST /api/recording/start` - 녹화 시작
- `POST /api/recording/stop` - 녹화 정지
- `GET /api/recording/status` - 녹화 상태
- `POST /api/snapshot` - 스냅샷 캡처

### 파일 관리
- `GET /api/files` - 파일 목록
- `GET /api/files/{type}/{filename}` - 파일 다운로드
- `DELETE /api/files/{type}/{filename}` - 파일 삭제

### 카메라 관리
- `POST /api/camera/switch` - 카메라 전환
- `POST /api/camera/refresh` - 카메라 재감지
- `GET /api/camera/detect` - 사용 가능한 카메라 확인

## ⌨️ 키보드 단축키

- `Ctrl+R` - 녹화 시작/정지
- `Ctrl+S` - 스냅샷 캡처
- `Ctrl+L` - 파일 목록 새로고침

## 📋 시스템 요구사항

### 하드웨어
- **Raspberry Pi 4** (권장) 또는 Pi 3B+
- **Raspberry Pi Camera Module** V1/V2/HQ
- **MicroSD 카드** 16GB 이상
- **전원 어댑터** 5V 3A

### 소프트웨어
- **Raspberry Pi OS** Bookworm (64-bit 권장)
- **Python** 3.11+
- **libcamera** (기본 설치됨)
- **UV** (자동 설치됨)

## 🔍 문제 해결

### 카메라가 감지되지 않는 경우
```bash
# 카메라 연결 확인
rpicam-hello --list-cameras

# 권한 확인
groups $USER  # video 그룹 포함 확인

# 카메라 재감지
curl -X POST http://localhost:8000/api/camera/refresh
```

### 의존성 문제
```bash
# 환경 재설정
rm -rf .venv
./fabcam.sh
```

## 🚀 성능 최적화

- **UV 패키지 매니저**: pip 대비 10-20배 빠른 설치
- **rpicam 네이티브**: OpenCV 대비 높은 성능
- **MJPEG 스트리밍**: 낮은 지연시간
- **비동기 처리**: FastAPI 기반 고성능

## 📄 라이센스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일 참조

## 🤝 기여

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 지원

문제가 있으시면 [Issues](https://github.com/JamesjinKim/fabcam/issues)에 보고해 주세요.

---

**🎯 FabCam - 간단하고 강력한 Raspberry Pi CCTV 솔루션**