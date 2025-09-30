#!/usr/bin/env python3
"""
Hailo AI Kit 객체 감지 엔진
기존 Hailo-apps-infra를 활용한 실시간 객체 감지

Author: SHT Team
Date: 2025-09-28
"""

import os
import sys
import time
import threading
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
import numpy as np
import cv2
from dataclasses import dataclass
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

try:
    import hailo
    from hailo_apps.hailo_app_python.core.gstreamer.gstreamer_app import app_callback_class
    from hailo_apps.hailo_app_python.apps.detection_simple.detection_pipeline_simple import GStreamerDetectionApp
    HAILO_AVAILABLE = True
except ImportError:
    print("⚠️ Hailo Platform이 설치되지 않음. 모의 모드로 실행됩니다.")
    HAILO_AVAILABLE = False


@dataclass
class Detection:
    """객체 감지 결과"""
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    class_id: int


class HailoCallback(app_callback_class):
    """Hailo 콜백 클래스 - 감지 결과 수집"""

    def __init__(self):
        super().__init__()
        self.latest_detections = []
        self.detection_lock = threading.Lock()
        self.frame_count = 0

    def get_detections(self) -> List[Detection]:
        """최신 감지 결과 반환"""
        with self.detection_lock:
            return self.latest_detections.copy()

    def clear_detections(self):
        """감지 결과 초기화"""
        with self.detection_lock:
            self.latest_detections = []


def detection_callback(pad, info, user_data: HailoCallback):
    """감지 콜백 함수"""
    user_data.increment()
    buffer = info.get_buffer()

    if buffer is None:
        return Gst.PadProbeReturn.OK

    detections = []

    try:
        # Hailo 감지 결과 파싱
        roi = hailo.get_roi_from_buffer(buffer)
        hailo_detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

        for detection in hailo_detections:
            label = detection.get_label()
            confidence = detection.get_confidence()
            bbox = detection.get_bbox()

            # Detection 객체 생성
            det = Detection(
                label=label,
                confidence=confidence,
                bbox=(int(bbox.xmin()), int(bbox.ymin()),
                      int(bbox.xmax()), int(bbox.ymax())),
                class_id=0  # YOLOv5에서 클래스 ID 추출 필요시 확장
            )
            detections.append(det)

    except Exception as e:
        print(f"⚠️ 감지 콜백 오류: {e}")

    # 감지 결과 업데이트
    with user_data.detection_lock:
        user_data.latest_detections = detections

    # 통계 출력 (선택적)
    if user_data.get_count() % 30 == 0:  # 30프레임마다
        print(f"Frame {user_data.get_count()}: {len(detections)}개 객체 감지")
        for det in detections:
            print(f"  - {det.label}: {det.confidence:.2f}")

    return Gst.PadProbeReturn.OK


class HailoDetector:
    """
    Hailo AI Kit을 사용한 객체 감지 엔진

    기존 hailo-apps-infra의 GStreamer 파이프라인을 활용하여
    백그라운드에서 실시간 객체 감지를 수행
    """

    def __init__(self, model_path: str = "models/yolov5s.hef",
                 confidence_threshold: float = 0.5):
        """
        Args:
            model_path: HEF 모델 파일 경로
            confidence_threshold: 감지 신뢰도 임계값
        """
        self.model_path = Path(model_path)
        self.confidence_threshold = confidence_threshold
        self.is_initialized = False
        self.is_running = False

        # GStreamer 앱과 콜백
        self.app = None
        self.callback_data = None
        self.app_thread = None

        # 성능 통계
        self.stats = {
            'total_frames': 0,
            'detection_count': 0,
            'avg_inference_time': 0.0,
            'last_detection_time': 0
        }

        print(f"🤖 HailoDetector 초기화 완료")
        print(f"   - 모델: {self.model_path}")
        print(f"   - 신뢰도 임계값: {self.confidence_threshold}")
        print(f"   - Hailo 사용 가능: {HAILO_AVAILABLE}")

        # .env 파일 설정
        self._setup_environment()

    def _setup_environment(self):
        """환경 변수 설정"""
        project_root = Path(__file__).resolve().parent
        env_file = project_root / "hailo-rpi5-examples" / ".env"

        if env_file.exists():
            os.environ["HAILO_ENV_FILE"] = str(env_file)
            print(f"✓ Hailo 환경 파일 설정: {env_file}")
        else:
            print(f"⚠️ Hailo 환경 파일 없음: {env_file}")

    def initialize(self) -> bool:
        """
        Hailo 감지 시스템 초기화

        Returns:
            bool: 초기화 성공 여부
        """
        if not HAILO_AVAILABLE:
            print("⚠️ Hailo Platform 미사용. 모의 모드로 동작합니다.")
            self.is_initialized = True
            return True

        try:
            # 모델 파일 확인
            if not self.model_path.exists():
                print(f"❌ 모델 파일이 없습니다: {self.model_path}")
                return False

            print(f"🔧 Hailo 감지 시스템 초기화 중...")

            # 콜백 데이터 초기화
            self.callback_data = HailoCallback()

            # GStreamer 앱 생성
            self.app = GStreamerDetectionApp(detection_callback, self.callback_data)

            print("✓ GStreamer 감지 앱 생성 완료")

            self.is_initialized = True
            print("🚀 Hailo 감지 시스템 초기화 완료!")

            return True

        except Exception as e:
            print(f"❌ Hailo 감지 시스템 초기화 실패: {e}")
            return False

    def start_detection(self) -> bool:
        """백그라운드 감지 시작"""
        if not self.is_initialized:
            print("⚠️ 먼저 initialize()를 호출하세요")
            return False

        if self.is_running:
            print("⚠️ 이미 감지가 실행 중입니다")
            return True

        if not HAILO_AVAILABLE:
            print("ℹ️ 모의 모드: 감지 시뮬레이션 시작")
            self.is_running = True
            return True

        try:
            print("🎬 백그라운드 객체 감지 시작...")

            # 별도 스레드에서 GStreamer 앱 실행
            def run_app():
                try:
                    self.app.run()
                except Exception as e:
                    print(f"❌ GStreamer 앱 실행 오류: {e}")
                    self.is_running = False

            self.app_thread = threading.Thread(target=run_app, daemon=True)
            self.app_thread.start()

            # 앱 시작 대기
            time.sleep(2)
            self.is_running = True

            print("✓ 백그라운드 감지 시작됨")
            return True

        except Exception as e:
            print(f"❌ 감지 시작 실패: {e}")
            return False

    def get_latest_detections(self) -> List[Detection]:
        """
        최신 감지 결과 반환

        Returns:
            List[Detection]: 감지된 객체 리스트
        """
        if not self.is_running:
            return []

        if not HAILO_AVAILABLE:
            # 모의 감지 결과
            return [
                Detection("person", 0.85, (100, 100, 200, 300), 0),
                Detection("car", 0.72, (300, 150, 500, 350), 2)
            ]

        if self.callback_data:
            detections = self.callback_data.get_detections()

            # 신뢰도 필터링
            filtered = [d for d in detections if d.confidence >= self.confidence_threshold]

            # 통계 업데이트
            self._update_stats(len(filtered))

            return filtered

        return []

    def _update_stats(self, detection_count: int):
        """성능 통계 업데이트"""
        self.stats['total_frames'] += 1
        self.stats['detection_count'] += detection_count
        self.stats['last_detection_time'] = time.time()

    def get_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        frame_count = 0
        if self.callback_data:
            frame_count = self.callback_data.get_count()

        return {
            'total_frames': frame_count,
            'total_detections': self.stats['detection_count'],
            'is_running': self.is_running,
            'model_loaded': self.is_initialized,
            'last_detection_time': self.stats['last_detection_time']
        }

    def stop_detection(self):
        """감지 중지"""
        print("🛑 객체 감지 중지 중...")

        self.is_running = False

        if HAILO_AVAILABLE and self.app:
            try:
                # GStreamer 앱 종료는 복잡하므로 스레드 종료만 대기
                if self.app_thread and self.app_thread.is_alive():
                    # 스레드가 자연스럽게 종료되도록 대기
                    pass
            except Exception as e:
                print(f"⚠️ 앱 종료 중 오류: {e}")

        print("✓ 객체 감지 중지됨")

    def cleanup(self):
        """리소스 정리"""
        print("🧹 HailoDetector 리소스 정리 중...")

        self.stop_detection()

        # 콜백 데이터 정리
        if self.callback_data:
            self.callback_data.clear_detections()

        print("✓ HailoDetector 정리 완료")

    def __enter__(self):
        """Context Manager 진입"""
        if not self.initialize():
            raise RuntimeError("HailoDetector 초기화 실패")
        if not self.start_detection():
            raise RuntimeError("HailoDetector 감지 시작 실패")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager 종료"""
        self.cleanup()


def test_hailo_detector():
    """HailoDetector 테스트 함수"""
    print("🧪 HailoDetector 테스트 시작")

    try:
        detector = HailoDetector()

        if not detector.initialize():
            print("❌ 초기화 실패")
            return

        if not detector.start_detection():
            print("❌ 감지 시작 실패")
            return

        print("⏳ 5초간 감지 테스트...")
        for i in range(5):
            time.sleep(1)
            detections = detector.get_latest_detections()
            print(f"  {i+1}초: {len(detections)}개 객체 감지")

            for det in detections:
                print(f"    - {det.label}: {det.confidence:.2f} at {det.bbox}")

        # 성능 통계
        stats = detector.get_stats()
        print(f"📊 성능 통계:")
        print(f"   - 총 프레임: {stats['total_frames']}")
        print(f"   - 총 감지: {stats['total_detections']}")
        print(f"   - 실행 상태: {stats['is_running']}")

        detector.cleanup()
        print("✅ 테스트 완료")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")


if __name__ == "__main__":
    test_hailo_detector()