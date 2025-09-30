# CLAUDE.md - 개발자 기술 문서

## 프로젝트 개요

**SHT 듀얼 LIVE AI 카메라** - 라즈베리파이 5 + Hailo AI Kit 기반 지능형 CCTV 시스템
- **목적**: 실시간 CCTV 스트리밍 + 24시간 자동 녹화 + AI 객체 감지
- **핵심**: FastAPI + Picamera2 + Hailo-8L NPU + 통합 아키텍처
- **특징**: 웹 스트리밍, 연속 녹화, 실시간 AI 감지 독립 동작

## 시스템 아키텍처

### 기술 스택
- **하드웨어**: Raspberry Pi 5 (BCM2712), OV5647 카메라 × 2, Hailo-8L AI Kit (13 TOPS)
- **백엔드**: FastAPI + Picamera2 + GPU H.264 인코딩 + Hailo NPU AI 추론
- **프론트엔드**: Vanilla JS + 반응형 UI + 실시간 모니터링 + AI 감지 오버레이
- **스토리지**: 30초 단위 MP4 파일 자동 저장 + AI 이벤트 스냅샷
- **AI 모델**: YOLOv5/YOLOv11 (Hailo 최적화)

### 파일 구조
```
fabcam/
├── webmain.py             # 통합 메인 서버 (스트리밍 + 녹화 + AI)
├── config_manager.py      # 설정 관리자 모듈
├── config.json            # JSON 설정 파일
├── hailo_detector.py      # Hailo AI 감지 엔진 (신규)
├── models/                # AI 모델 저장소 (신규)
│   ├── yolov5s.hef        # Hailo-8L 최적화 YOLOv5
│   ├── yolov11n.hef       # Hailo-8L 최적화 YOLOv11
│   └── labels.txt         # COCO 클래스 라벨
├── web/                   # 웹 인터페이스
│   ├── static/
│   │   ├── index.html     # 듀얼 뷰 메인 페이지
│   │   ├── style.css      # 스타일시트 (AI 오버레이 추가)
│   │   └── script.js      # 클라이언트 로직 (바운딩박스 표시)
│   └── api.py             # FastAPI 라우터 (AI API 추가)
├── videos/                # 녹화 파일 저장소
│   ├── cam0/              # 카메라 0 녹화 파일
│   └── cam1/              # 카메라 1 녹화 파일
├── snapshots/             # AI 이벤트 스냅샷 (신규)
│   ├── detections/        # 객체 감지 이미지
│   └── alerts/            # 알림 트리거 이미지
├── hailo-rpi5-examples/   # Hailo 공식 예제
├── test_hailo.py          # Hailo NPU 테스트 스크립트
├── README.md              # 사용자 가이드
└── CLAUDE.md              # 개발자 문서 (현재 파일)
```

## 핵심 기능

### 1. 실시간 웹 스트리밍
- **MJPEG 스트리밍**: 30fps, 다중 클라이언트 지원 (최대 2명)
- **듀얼/싱글 뷰**: 실시간 전환, 카메라 개별 제어
- **해상도 지원**: 640×480 (480p), 1280×720 (720p)
- **거울모드**: 좌우 반전 (`libcamera.Transform(hflip=True)`)

### 2. 24시간 자동 녹화
- **연속 녹화**: 30초 단위 끊김없는 녹화 (24/7)
- **GPU 가속**: H.264 하드웨어 인코딩 (5Mbps, 30fps)
- **독립 동작**: 웹 접속과 무관하게 백그라운드 동작
- **자동 관리**: 타임스탬프 파일명, 실시간 통계

### 3. 웹 인터페이스
- **실시간 모니터링**: LIVE/OFFLINE 상태, FPS, 프레임 수
- **직관적 컨트롤**: 카메라 전환, 해상도 변경
- **반응형 디자인**: 모바일/데스크톱 지원
- **하트비트 체크**: 3초 간격 연결 상태 확인

### 4. 실시간 AI 객체 감지 🆕
- **NPU 가속**: Hailo-8L (13 TOPS) 전용 AI 추론
- **다중 모델**: YOLOv5s, YOLOv11n 지원
- **실시간 처리**: 10-15 FPS AI 감지 (독립 스레드)
- **바운딩박스**: 웹 UI에 실시간 오버레이 표시
- **이벤트 감지**: 사람, 차량, 동물 등 특정 객체 알림
- **스냅샷 저장**: 감지 순간 이미지 자동 캡처

### 5. JSON 설정 시스템
- **유연한 설정 관리**: config.json 파일로 모든 설정 중앙화
- **실시간 적용**: 서버 재시작 없이 설정 변경 가능
- **기본값 제공**: 누락된 설정은 자동으로 기본값 적용
- **점 표기법**: `recording.bitrate` 형태로 직관적 접근

## 핵심 클래스

### 1. CameraManager
**역할**: 카메라 스트리밍 및 모드 관리
```python
class CameraManager:
    def start_camera_stream(self, camera_id: int) -> bool
    def enable_dual_mode(self) -> bool
    def generate_stream(self, client_ip: str, camera_id: int = None)
    def get_stats(self) -> Dict[str, Any]
```

### 2. GPURecorder
**역할**: GPU 가속 연속 녹화
```python
class GPURecorder:
    def start_continuous_recording(self, interval: int = 31)
    def _record_single_video(self, duration: int = 31)
    def stop_recording(self)
```

### 3. CCTVWebAPI
**역할**: FastAPI 라우팅 및 API 엔드포인트
```python
class CCTVWebAPI:
    @app.get("/stream/{camera_id}")
    @app.post("/api/dual_mode/{enable}")
    @app.get("/api/stats")
```

### 4. ConfigManager
**역할**: JSON 설정 파일 관리
```python
class ConfigManager:
    def get(self, path: str, default=None) -> Any
    def set(self, path: str, value: Any) -> bool
    def get_bitrate(self) -> int
    def get_segment_duration(self) -> int
```

### 5. HailoDetector 🆕
**역할**: Hailo NPU 기반 AI 객체 감지
```python
class HailoDetector:
    def __init__(self, model_path: str, confidence_threshold: float = 0.5)
    def start_detection(self, frame_queue: Queue)
    def detect_objects(self, frame: np.ndarray) -> List[Detection]
    def stop_detection(self)
    def get_detection_stats(self) -> Dict[str, Any]
    def reload(self) -> bool
```

## JSON 설정 시스템

### config.json 구조
```json
{
  "recording": {
    "enabled": true,
    "segment_duration": 31,      // 녹화 세그먼트 길이 (초)
    "overlap_duration": 1,       // 세그먼트 오버랩 (초)
    "bitrate": 5000000,          // 비트레이트 (bps)
    "framerate": 30,             // 프레임레이트 (fps)
    "resolution": [640, 480],    // 해상도 [가로, 세로]
    "cameras": {
      "0": {
        "enabled": true,
        "storage_path": "videos/cam0"
      },
      "1": {
        "enabled": true,
        "storage_path": "videos/cam1"
      }
    },
    "cleanup": {
      "enabled": false,          // 자동 정리 기능
      "max_age_days": 30,        // 최대 보관 일수
      "min_free_space_gb": 10    // 최소 여유 공간 (GB)
    }
  },
  "streaming": {
    "max_clients": 2,            // 최대 동시 접속자 수
    "default_quality": "640x480",
    "mirror_mode": true,         // 거울모드 활성화
    "buffer_size": 10,           // 스트림 버퍼 크기
    "stats_interval": 2000,      // 통계 업데이트 간격 (ms)
    "heartbeat_interval": 3000   // 하트비트 체크 간격 (ms)
  },
  "ai_detection": {              // 🆕 AI 감지 설정
    "enabled": true,             // AI 감지 활성화
    "model_path": "models/yolov5s.hef",
    "confidence_threshold": 0.5, // 신뢰도 임계값
    "detection_interval": 3,     // 감지 프레임 간격 (매 3프레임)
    "max_detections": 20,        // 프레임당 최대 감지 수
    "npu_device": "/dev/hailo0", // NPU 장치 경로
    "cameras": {                 // 카메라별 AI 설정
      "0": {
        "enabled": true,
        "roi_zones": [[0,0], [640,480]], // 관심 영역
        "target_classes": ["person", "car", "dog", "cat"]
      },
      "1": {
        "enabled": true,
        "roi_zones": [[0,0], [640,480]],
        "target_classes": ["person", "car", "bicycle"]
      }
    },
    "events": {                  // 이벤트 알림 설정
      "enabled": true,
      "trigger_classes": ["person"], // 알림 트리거 클래스
      "cooldown_seconds": 10,    // 연속 알림 방지 간격
      "save_snapshots": true,    // 스냅샷 저장
      "snapshot_path": "snapshots/detections"
    }
  },
  "system": {
    "web_port": 8001,           // 웹 서버 포트
    "log_level": "INFO",        // 로그 레벨
    "gpu_memory_split": 256,    // GPU 메모리 할당 (MB)
    "npu_enabled": true         // 🆕 NPU 사용 활성화
  }
}
```

### ConfigManager 사용법
```python
from config_manager import config_manager

# 기본 사용법
segment_duration = config_manager.get_segment_duration()  # 31
bitrate = config_manager.get_bitrate()                    # 5000000

# 점 표기법으로 직접 접근
port = config_manager.get('system.web_port', 8001)       # 8001
mirror = config_manager.get('streaming.mirror_mode')     # True

# 🆕 AI 설정 접근
ai_enabled = config_manager.get('ai_detection.enabled')           # True
model_path = config_manager.get('ai_detection.model_path')        # "models/yolov5s.hef"
confidence = config_manager.get('ai_detection.confidence_threshold') # 0.5
target_classes = config_manager.get('ai_detection.cameras.0.target_classes') # ["person", "car", ...]

# 설정 변경
config_manager.set('recording.bitrate', 8000000)
config_manager.set('ai_detection.confidence_threshold', 0.7)  # 🆕 AI 신뢰도 변경
config_manager.save_config()

# 설정 리로드
config_manager.reload()
```

### 설정 변경 방법
1. **파일 직접 수정**: `config.json` 파일을 편집
2. **프로그래밍 방식**: ConfigManager의 `set()` 메서드 사용
3. **실시간 적용**: 대부분 설정은 다음 동작 시 자동 적용

## 중요 설정

### 카메라 구성
```python
config = picam2.create_video_configuration(
    main={
        "size": (width, height),
        "format": "YUV420"         # H.264 녹화 최적화
    },
    lores={
        "size": (width, height),
        "format": "RGB888"         # MJPEG 스트리밍
    },
    buffer_count=2,                # 레이턴시 최소화
    queue=False,
    transform=libcamera.Transform(hflip=True)  # 거울모드
)
```

### GPU 인코더 설정
```python
encoder = H264Encoder(
    bitrate=5000000,               # 5Mbps
    repeat=True,                   # SPS/PPS 반복
    iperiod=30,                    # I-프레임 주기
    framerate=30                   # 30fps
)
```

## 운영 가이드

### 시작/중지
```bash
# 시스템 시작 (통합 서버)
python3 webmain.py

# 웹 접속
http://라즈베리파이IP:8001

# 시스템 종료
Ctrl+C 또는 웹 UI에서 종료
```

### 성능 지표
| 기능 | CPU | 메모리 | NPU | 대역폭 | 비고 |
|------|-----|--------|-----|--------|------|
| 듀얼 스트리밍 (480p) | ~10% | 50MB | 0% | ~2Mbps | MJPEG |
| 듀얼 스트리밍 (720p) | ~15% | 70MB | 0% | ~4Mbps | MJPEG |
| 듀얼 녹화 (720p) | ~12% | 60MB | 0% | 5Mbps/카메라 | H.264 |
| 🆕 **듀얼 AI 감지** | **~8%** | **+80MB** | **~70%** | **0Mbps** | **Hailo-8L** |
| **전체 시스템 (AI 포함)** | **~33%** | **~200MB** | **~70%** | **~14Mbps** | **모든 기능** |

### 🆕 AI 성능 세부사항
- **추론 속도**: 10-15 FPS (640×480 입력)
- **레이턴시**: 50-80ms/프레임
- **NPU 사용률**: 60-80% (듀얼 카메라)
- **전력 소비**: +3-5W (NPU 추가)
- **감지 정확도**: mAP 0.5+ (COCO 데이터셋)

### 문제 해결

#### 카메라 연결 확인
```bash
rpicam-hello --list-cameras
python3 -c "from picamera2 import Picamera2; print('OK')"
```

#### 🆕 Hailo NPU 확인
```bash
# NPU 하드웨어 확인
lspci | grep -i hailo
sudo hailortcli fw-control identify

# NPU 장치 파일 확인
ls -la /dev/hailo*

# NPU 드라이버 상태
lsmod | grep hailo

# NPU Python 바인딩 테스트
python3 test_hailo.py
```

#### 성능 최적화
```bash
# GPU 메모리 확인/설정 (256MB 권장)
vcgencmd get_mem gpu
sudo raspi-config > Advanced Options > Memory Split

# 디스크 공간 확인
df -h videos/

# 프로세스 상태 확인
ps aux | grep python3
```

## 개발 정보

### 주요 아키텍처 개선
#### 2025-09-23 (통합 시스템)
1. **카메라 인스턴스 재사용**: 중복 생성 방지, 안정성 향상
2. **독립적 녹화 시스템**: 웹 접속과 무관한 24시간 연속 녹화
3. **리소스 분리**: 스트리밍(lores) vs 녹화(main) 스트림 분리
4. **오류 복구**: 웹 클라이언트 접속 시 녹화 중단 문제 해결

#### 2025-09-23 (JSON 설정 시스템)
1. **설정 중앙화**: 모든 하드코딩 값을 config.json으로 이동
2. **ConfigManager 구현**: 설정 관리 전용 클래스 도입
3. **유연한 설정**: 세그먼트 길이, 비트레이트 등 운영 중 변경 가능
4. **기본값 제공**: 설정 누락 시 안전한 기본값 자동 적용

#### 🆕 2025-09-28 (Hailo AI Kit 통합)
1. **NPU 연동**: Hailo-8L (13 TOPS) AI 가속기 완전 통합
2. **AI 감지 엔진**: HailoDetector 클래스 설계 및 구현
3. **병렬 처리**: 스트리밍/녹화와 독립적인 AI 추론 파이프라인
4. **설정 확장**: AI 관련 설정을 config.json에 통합
5. **성능 최적화**: CPU 8% 추가로 실시간 AI 감지 구현

### 코딩 가이드라인
- **Python**: PEP 8 준수
- **비동기**: FastAPI async/await 활용
- **로깅**: 상세한 디버그 정보 포함
- **오류 처리**: 복구 가능한 예외 처리

### 의존성
```bash
# 🆕 Hailo AI Kit 패키지 (우선 설치)
sudo apt install hailo-all

# 시스템 패키지
sudo apt install python3-picamera2 python3-libcamera ffmpeg

# Python 패키지
pip3 install fastapi uvicorn opencv-python numpy psutil

# 🆕 Hailo Python 바인딩 (이미 hailo-all에 포함)
# python3-hailort hailo-tappas-core
```

---

**마지막 업데이트**: 2025-09-28 (Hailo AI Kit 통합 + AI 객체 감지 시스템 추가)