# FabCam CCTV 시스템

🎥 **라즈베리 파이 기반 듀얼 카메라 보안 모니터링 시스템**

![System Status](https://img.shields.io/badge/Status-운영중-green)
![Cameras](https://img.shields.io/badge/Cameras-2개_지원-blue)
![Resolution](https://img.shields.io/badge/Resolution-640×480@30fps-orange)

## 📋 주요 기능

### 🔴 **블랙박스 기능 (핵심)**
- **30초 자동 분할 녹화**: 차량용 블랙박스처럼 30초 단위 세그먼트로 저장
- **H.264 압축**: 고효율 비디오 압축으로 저장 공간 절약
- **자동 재시작**: 세그먼트 완료 시 자동으로 다음 녹화 시작
- **스마트 리소스 관리**: 스트리밍 시작 시 자동 일시정지, 종료 시 자동 재개

### 📹 **실시간 스트리밍**
- **MJPEG 스트리밍**: 웹 브라우저에서 실시간 모니터링
- **다중 클라이언트 지원**: 여러 사용자가 동시 접속 가능
- **저지연**: 500ms 이하 지연시간
- **자동 연결**: 시스템 시작 시 자동으로 스트리밍 활성화

### 📸 **스냅샷 캡처**
- **다중 해상도**: 640×480, 1280×720, 1920×1080 지원
- **즉시 캡처**: 버튼 클릭으로 현재 화면 저장
- **고품질**: JPEG 형식으로 선명한 이미지 저장

### 🎬 **수동 녹화 (고급 기능)**
- **긴 영상 녹화**: 연속 파일로 장시간 녹화
- **사용자 제어**: 시작/중지 수동 조작
- **별도 저장**: 블랙박스와 구분된 저장 위치

## 🛠 시스템 요구사항

### 하드웨어
- **라즈베리 파이 4** (권장) 또는 Pi 5
- **듀얼 OV5647 카메라 모듈** (카메라 0번, 1번)
- **MicroSD 카드** 32GB 이상 (Class 10)
- **전원 어댑터** 5V 3A

### 소프트웨어  
- **Raspberry Pi OS** Bookworm (64-bit)
- **Python** 3.11+
- **libcamera-apps** (기본 설치됨)
- **FastAPI, OpenCV** (자동 설치)

## 🚀 설치 및 실행

### 1. 카메라 연결 확인
```bash
# 카메라 목록 확인
rpicam-hello --list-cameras

# 예상 출력:
# Available cameras
# 0 : ov5647 [2592x1944 10-bit GBRG] (/base/axi/.../ov5647@36)
# 1 : ov5647 [2592x1944 10-bit GBRG] (/base/axi/.../ov5647@36)
```

### 2. 시스템 설정
```bash
# 저장소 클론
git clone https://github.com/JamesjinKim/fabcam.git
cd fabcam/FabCam

# Python 의존성 설치
pip install fastapi uvicorn opencv-python psutil pathlib

# 저장 디렉토리 생성 (자동 생성됨)
mkdir -p static/{images,videos,rec/camera0,rec/camera1}
```

### 3. 서버 시작
```bash
# FabCam 서버 실행
python main.py

# 서버 시작 확인 메시지:
# 🚀 블랙박스 카메라 매니저 초기화 (스트림 + 연속녹화 + 수동녹화)
# 📷 감지된 카메라: 2개
# INFO: Uvicorn running on http://0.0.0.0:8000
```

### 4. 웹 접속
- **로컬**: http://localhost:8000
- **네트워크**: http://[라즈베리파이_IP]:8000

## 📖 사용 방법

### 🔴 블랙박스 녹화 시작하기

1. **웹 브라우저**에서 FabCam 접속
2. 각 카메라 영역에서 **"●REC 시작"** 버튼 클릭
3. **30초마다 자동으로 새 파일 생성** (예: `rec_0_20250822_143025.mp4`)
4. 녹화 중지: **"⏹ 블랙박스 중지"** 버튼 클릭

```bash
# API로 블랙박스 제어 (선택사항)
curl -X POST http://localhost:8000/api/camera/0/start_continuous
curl -X POST http://localhost:8000/api/camera/0/stop_continuous
```

### 📸 스냅샷 캡처하기

1. **해상도 선택**: 드롭다운에서 원하는 해상도 선택
2. **"📷 캡처"** 버튼 클릭
3. 이미지 저장 위치: `static/images/[해상도]/`

### 🎬 수동 녹화 (고급)

1. 하단 **"수동 녹화"** 섹션에서 **"⏺ 긴 영상 녹화"** 클릭
2. 원하는 시점에 **"⏹ 중지"** 클릭
3. 연속 파일로 저장: `static/videos/`

### 📁 파일 관리

```bash
# 저장된 파일 확인
ls static/rec/camera0/        # 블랙박스 녹화 파일
ls static/rec/camera1/        # 블랙박스 녹화 파일  
ls static/images/640x480/     # 스냅샷 이미지
ls static/videos/             # 수동 녹화 파일
```

**자동 정리**: 블랙박스는 48개 파일(24시간) 초과 시 오래된 파일 자동 삭제

## 🔧 주요 API 엔드포인트

### 스트리밍
- `GET /video_feed/0` - 카메라 0번 실시간 스트림
- `GET /video_feed/1` - 카메라 1번 실시간 스트림

### 블랙박스 제어
- `POST /api/camera/{id}/start_continuous` - 연속 녹화 시작
- `POST /api/camera/{id}/stop_continuous` - 연속 녹화 중지
- `GET /api/camera/{id}/continuous_status` - 녹화 상태 확인

### 스냅샷
- `POST /api/snapshot/{id}?resolution=hd` - 스냅샷 캡처

### 시스템 정보
- `GET /api/camera/status` - 카메라 상태
- `GET /api/system/status` - 시스템 리소스 상태

## ⚡ 성능 특징

### 리소스 효율성
- **CPU 사용률**: 라즈베리 파이에서 70% 이하 유지
- **메모리 사용**: 512MB 이하
- **해상도**: 640×480@30fps 최적화 (안정성 우선)

### 안정성 기능
- **스마트 리소스 관리**: 스트리밍과 녹화 간 자동 전환
- **자동 복구**: 카메라 오류 시 자동 재시도
- **프로세스 모니터링**: 백그라운드 상태 감시

## 🔍 문제 해결

### 카메라가 인식되지 않는 경우
```bash
# 1. 하드웨어 연결 확인
rpicam-hello --list-cameras

# 2. 카메라 인터페이스 활성화
sudo raspi-config
# → Interface Options → Camera → Enable

# 3. 재부팅
sudo reboot

# 4. 시스템 재시작
python main.py
```

### 스트리밍이 끊어지는 경우
```bash
# 네트워크 연결 확인
ping [라즈베리파이_IP]

# 브라우저 새로고침
Ctrl + F5

# 서버 재시작
python main.py
```

### 녹화 파일이 생성되지 않는 경우
```bash
# 디스크 공간 확인
df -h

# 권한 확인
chmod 755 static/
chmod -R 755 static/rec/

# 카메라 상태 확인
curl http://localhost:8000/api/camera/status
```

## 📊 저장 위치

```
FabCam/
├── static/
│   ├── rec/                    # 🔴 블랙박스 녹화
│   │   ├── camera0/           #   rec_0_20250822_143025.mp4
│   │   └── camera1/           #   rec_1_20250822_143055.mp4
│   ├── videos/                # 🎬 수동 녹화  
│   │   └── manual_20250822_143030_cam0.mp4
│   └── images/                # 📸 스냅샷
│       ├── 640x480/
│       ├── 1280x720/
│       └── 1920x1080/
```

## 💡 사용 팁

### 블랙박스 최적화
- **24시간 자동 운영**: 시스템 부팅 시 자동으로 블랙박스 시작
- **저장 공간 관리**: 48개 파일(24시간) 자동 순환 저장
- **안정성 우선**: 640×480 해상도로 장시간 안정 운영

### 모니터링 권장사항  
- **원격 접속**: 같은 네트워크의 PC/모바일에서 모니터링
- **다중 접속**: 여러 디바이스에서 동시 모니터링 가능
- **실시간 확인**: 스트리밍으로 실시간 상황 파악

## 📞 지원

- **GitHub**: https://github.com/JamesjinKim/fabcam
- **이슈 리포트**: GitHub Issues 탭 활용
- **문서**: `CLAUDE.md` (개발자용), `CAMERA_DIAGNOSIS.md` (하드웨어 진단)

---

**🎯 FabCam - 간단하고 강력한 라즈베리 파이 CCTV 솔루션**  
*블랙박스 기능으로 24시간 안심 보안 모니터링* 🛡️