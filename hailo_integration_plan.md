# Fabcam + Hailo 통합 계획

## 현재 상황 분석
- **Fabcam**: Picamera2 기반 듀얼 CCTV 시스템 (스트리밍 + 녹화)
- **Hailo 예제**: GStreamer 파이프라인 기반 AI 감지
- **핵심 과제**: 두 시스템 간 프레임 공유 및 동기화

## 추천 통합 방식

### 방식 1: 병렬 파이프라인 (권장) ✅
```
[Picamera2] → [Frame Buffer] → [Fabcam 스트리밍/녹화]
                    ↓
              [Hailo AI 감지]
```

**장점**:
- 기존 fabcam 코드 최소 수정
- 독립적 동작으로 안정성 보장
- AI 처리 지연이 스트리밍에 영향 없음

**구현 방법**:
1. Picamera2 프레임을 공유 메모리로 복사
2. Hailo는 별도 스레드에서 프레임 처리
3. 감지 결과를 웹소켓으로 전송

### 방식 2: GStreamer 통합
```
[v4l2src] → [tee] → [Hailo] → [오버레이] → [H264 인코더] → [파일/스트림]
```

**장점**:
- Hailo 예제 직접 활용 가능
- GStreamer의 최적화된 파이프라인

**단점**:
- Picamera2 코드 전면 재작성 필요
- 듀얼 카메라 처리 복잡

## 단계별 구현 계획

### Phase 1: Hailo 예제 실행 및 학습
1. `detection_simple.py` 분석 및 실행
2. Hailo Python API 이해
3. 모델 로딩 및 추론 테스트

### Phase 2: 독립형 Hailo 모듈 개발
```python
# hailo_detector.py
class HailoDetector:
    def __init__(self, model_path):
        self.device = VDevice()
        self.model = self.device.create_infer_model(model_path)

    def detect(self, frame):
        # numpy array → Hailo 추론
        return detections
```

### Phase 3: Fabcam 통합
```python
# webmain.py 수정
from hailo_detector import HailoDetector

class CameraManager:
    def __init__(self):
        self.detector = HailoDetector("yolo11.hef")

    def process_frame(self, frame):
        # 5프레임마다 AI 처리
        if self.frame_count % 5 == 0:
            detections = self.detector.detect(frame)
            self.broadcast_detections(detections)
```

### Phase 4: 웹 UI 개선
- Canvas 오버레이로 바운딩박스 표시
- 실시간 객체 카운트 표시
- 감지 이벤트 알림

## 필요 리소스

### 모델 파일
```bash
# YOLOv8n Hailo 모델 다운로드
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/yolov8n.hef
```

### 추가 패키지
```bash
pip install hailo_platform
pip install gstreamer-python
```

## 성능 목표
- **AI 처리**: 10 FPS (듀얼 카메라)
- **레이턴시**: < 100ms
- **정확도**: mAP > 0.5
- **CPU 사용률**: < 30%

## 주요 파일 구조
```
fabcam/
├── webmain.py          # [수정] Hailo 통합
├── hailo_detector.py   # [신규] AI 감지 모듈
├── models/
│   ├── yolo11n.hef     # Hailo 컴파일 모델
│   └── labels.txt      # 클래스 라벨
└── web/
    └── static/
        └── script.js   # [수정] 바운딩박스 표시
```

## 참고 코드 위치
- 기본 감지: `hailo-rpi5-examples/basic_pipelines/detection_simple.py`
- Hailo API: `hailo-apps-infra/core/hailo/`
- 콜백 처리: `app_callback()` 함수 패턴 활용