# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

FabCam은 라즈베리 파이 기반의 CCTV 시스템으로, 듀얼 카메라를 지원하며 실시간 스트리밍, 연속 녹화, 수동 녹화 기능을 제공합니다. `rpicam-vid`와 `rpicam-still`을 사용하여 하드웨어에 접근하고, FastAPI 웹 인터페이스와 MJPEG 스트리밍을 제공합니다.

## 명령어

### 애플리케이션 실행
```bash
# FastAPI 서버 시작
python main.py

# uvicorn으로 직접 실행
uvicorn main:app --host 0.0.0.0 --port 8000 --reload=False
```

### 카메라 시스템 테스트
```bash
# 카메라 감지 테스트
rpicam-hello --list-cameras

# 개별 카메라 스트리밍 테스트 (5초)
rpicam-vid --camera 0 --width 640 --height 480 --framerate 30 --codec mjpeg --output - --timeout 5000 --nopreview
rpicam-vid --camera 1 --width 640 --height 480 --framerate 30 --codec mjpeg --output - --timeout 5000 --nopreview

# 테스트 스냅샷 캡처
rpicam-still --camera 0 --width 640 --height 480 -o test_cam0.jpg -t 100 --nopreview
rpicam-still --camera 1 --width 640 --height 480 -o test_cam1.jpg -t 100 --nopreview
```

### 시스템 의존성
```bash
# rpicam 도구 설치 확인 (라즈베리 파이 OS Bullseye+)
sudo apt update
sudo apt install python3-picamera2

# Python 의존성 확인 (requirements.txt 없음 - 시스템 패키지 사용)
python3 -c "import fastapi, uvicorn, subprocess, threading, psutil; print('의존성 확인 완료')"
```

## 아키텍처

### 핵심 컴포넌트

1. **SharedStreamManager** (`camera.py:19-279`)
   - 단일 카메라 프로세스로 다중 웹 클라이언트 서비스
   - stdout 버퍼링 문제 해결을 위해 FIFO 파이프 사용
   - 스트리밍 중 연속 녹화 자동 중단
   - 클라이언트 연결/해제 안전 처리

2. **ContinuousRecorder** (`camera.py:282-464`)
   - 30초 세그먼트 단위 H.264 블랙박스식 녹화
   - 연속 작동을 위한 자동 재시작 메커니즘
   - `static/rec/camera{N}/` 디렉토리에 저장
   - 스트리밍이나 수동 녹화 시작 시 자동 일시정지

3. **ManualRecorder** (`camera.py:466-604`)
   - 사용자 제어 H.264 형식 녹화
   - 작동 중 연속 녹화 임시 중단
   - 타임스탬프 네이밍으로 `static/videos/` 디렉토리에 저장

4. **CameraManager** (`camera.py:683-1220`)
   - 모든 카메라 작업의 중앙 조정자
   - 카메라 감지 및 초기화 처리
   - 스트리밍과 녹화 모드 간 리소스 충돌 관리
   - FastAPI 엔드포인트를 위한 통합 API 제공

### 주요 기술 세부사항

- **해상도**: 안정성을 위해 모든 작업을 640×480@30fps로 통일
- **스트리밍**: HTTP multipart 스트림을 통한 MJPEG
- **녹화**: 공간 효율성을 위한 H.264 MP4 파일
- **동시성**: 자동 모드 전환으로 카메라 충돌 방지
- **저장소**: 기능별로 `static/` 하위 디렉토리에 정리

### API 구조

FastAPI 앱(`main.py`)은 다음을 위한 REST 엔드포인트 제공:
- 실시간 카메라 스트리밍 (`/video_feed/{camera_id}`)
- 녹화 제어 (`/api/recording/start`, `/api/recording/stop`)
- 스냅샷 캡처 (`/api/snapshot/{camera_id}`)
- 시스템 모니터링 (`/api/system/status`)
- 파일 관리 (`/api/files`)

### 디렉토리 구조
```
FabCam/
├── camera.py          # 핵심 카메라 관리 클래스들
├── main.py           # FastAPI 웹 서버 및 API 엔드포인트
├── models.py         # Pydantic 데이터 모델
├── frontend/         # 웹 UI (HTML/CSS/JS)
├── static/
│   ├── images/       # 스냅샷 (해상도별 정리)
│   ├── videos/       # 수동 녹화
│   └── rec/          # 카메라별 연속 녹화
└── CAMERA_DIAGNOSIS.md # 하드웨어 상태 문서
```

### 하드웨어 통합

- 듀얼 OV5647 카메라가 있는 라즈베리 파이용 설계
- `rpicam-*` 명령어를 통한 libcamera 프레임워크 사용
- `rpicam-hello --list-cameras`를 통한 카메라 감지
- 시스템 상태를 위한 `psutil` 리소스 모니터링

### 개발 참고사항

- 시스템은 동시 접근보다 카메라 리소스 관리를 우선시
- 수동 녹화 시 연속 녹화 자동 중단
- 클라이언트 연결 시 스트리밍이 연속 녹화보다 우선
- 모든 카메라 작업에 자동 정리 및 재시작 로직 포함
- 오류 처리에 프로세스 모니터링 및 자동 복구 포함