#!/usr/bin/env python3
"""
간단한 AI 객체 감지 모듈
설치 완료를 기다리지 않고 사용 가능한 모의 AI 감지 시스템

Author: SHT Team
Date: 2025-09-28
"""

import time
import threading
import random
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import numpy as np
import cv2


@dataclass
class Detection:
    """객체 감지 결과"""
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    class_id: int


class SimpleAIDetector:
    """
    간단한 AI 객체 감지 엔진
    실제 Hailo 설치 완료 전까지 사용할 수 있는 모의 감지 시스템
    """

    def __init__(self, confidence_threshold: float = 0.5):
        """
        Args:
            confidence_threshold: 감지 신뢰도 임계값
        """
        self.confidence_threshold = confidence_threshold
        self.is_initialized = False
        self.is_running = False

        # 성능 통계
        self.stats = {
            'total_frames': 0,
            'detection_count': 0,
            'avg_inference_time': 0.0,
            'last_detection_time': 0
        }

        # COCO 클래스 라벨
        self.class_labels = [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
            'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
            'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
            'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee'
        ]

        # 스레드 안전성을 위한 락
        self._lock = threading.Lock()

        print(f"🤖 SimpleAIDetector 초기화 완료")
        print(f"   - 신뢰도 임계값: {self.confidence_threshold}")
        print(f"   - 모드: 모의 감지 (실제 Hailo 연결 전)")

    def initialize(self) -> bool:
        """
        AI 감지 시스템 초기화

        Returns:
            bool: 초기화 성공 여부
        """
        print(f"🔧 AI 감지 시스템 초기화 중...")

        # 모의 초기화 시간
        time.sleep(1)

        self.is_initialized = True
        print("🚀 AI 감지 시스템 초기화 완료!")

        return True

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        객체 감지 수행

        Args:
            frame: BGR 입력 프레임

        Returns:
            List[Detection]: 감지된 객체 리스트
        """
        if not self.is_initialized:
            print("⚠️ SimpleAIDetector가 초기화되지 않음")
            return []

        with self._lock:
            start_time = time.time()

            try:
                # 모의 추론 시간 (실제 NPU 처리 시뮬레이션)
                time.sleep(0.03)  # 30ms 모의 추론 시간

                # 프레임 크기 정보
                height, width = frame.shape[:2]

                # 모의 감지 결과 생성 (확률적)
                detections = []

                # 20% 확률로 사람 감지
                if random.random() < 0.2:
                    x1 = random.randint(0, width // 2)
                    y1 = random.randint(0, height // 2)
                    w = random.randint(width // 8, width // 4)
                    h = random.randint(height // 4, height // 2)
                    x2 = min(x1 + w, width - 1)
                    y2 = min(y1 + h, height - 1)

                    detection = Detection(
                        label="person",
                        confidence=random.uniform(0.7, 0.95),
                        bbox=(x1, y1, x2, y2),
                        class_id=0
                    )
                    detections.append(detection)

                # 10% 확률로 차량 감지
                if random.random() < 0.1:
                    x1 = random.randint(width // 4, width // 2)
                    y1 = random.randint(height // 2, height - 100)
                    w = random.randint(width // 6, width // 3)
                    h = random.randint(height // 8, height // 4)
                    x2 = min(x1 + w, width - 1)
                    y2 = min(y1 + h, height - 1)

                    car_labels = ['car', 'truck', 'bus', 'motorcycle']
                    label = random.choice(car_labels)

                    detection = Detection(
                        label=label,
                        confidence=random.uniform(0.6, 0.9),
                        bbox=(x1, y1, x2, y2),
                        class_id=2
                    )
                    detections.append(detection)

                # 신뢰도 필터링
                filtered_detections = [
                    d for d in detections
                    if d.confidence >= self.confidence_threshold
                ]

                # 성능 통계 업데이트
                inference_time = time.time() - start_time
                self._update_stats(inference_time, len(filtered_detections))

                return filtered_detections

            except Exception as e:
                print(f"❌ 객체 감지 오류: {e}")
                return []

    def _update_stats(self, inference_time: float, detection_count: int):
        """성능 통계 업데이트"""
        self.stats['total_frames'] += 1
        self.stats['detection_count'] += detection_count

        # 이동 평균으로 추론 시간 업데이트
        alpha = 0.1
        self.stats['avg_inference_time'] = (
            alpha * inference_time +
            (1 - alpha) * self.stats['avg_inference_time']
        )

        self.stats['last_detection_time'] = time.time()

    def get_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        fps = 1.0 / self.stats['avg_inference_time'] if self.stats['avg_inference_time'] > 0 else 0

        return {
            'total_frames': self.stats['total_frames'],
            'total_detections': self.stats['detection_count'],
            'avg_inference_time_ms': self.stats['avg_inference_time'] * 1000,
            'inference_fps': fps,
            'npu_utilization': random.uniform(60, 80),  # 모의 NPU 사용률
            'is_running': self.is_running,
            'model_loaded': self.is_initialized
        }

    def start_detection(self) -> bool:
        """감지 시작"""
        if not self.is_initialized:
            print("⚠️ 먼저 initialize()를 호출하세요")
            return False

        print("🎬 AI 객체 감지 시작...")
        self.is_running = True
        print("✓ AI 감지 활성화됨")
        return True

    def stop_detection(self):
        """감지 중지"""
        print("🛑 AI 객체 감지 중지 중...")
        self.is_running = False
        print("✓ AI 감지 중지됨")

    def cleanup(self):
        """리소스 정리"""
        print("🧹 SimpleAIDetector 리소스 정리 중...")
        self.stop_detection()
        print("✓ SimpleAIDetector 정리 완료")

    def __enter__(self):
        """Context Manager 진입"""
        if not self.initialize():
            raise RuntimeError("SimpleAIDetector 초기화 실패")
        if not self.start_detection():
            raise RuntimeError("SimpleAIDetector 감지 시작 실패")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager 종료"""
        self.cleanup()


def draw_detections(frame: np.ndarray, detections: List[Detection]) -> np.ndarray:
    """
    프레임에 감지 결과 그리기

    Args:
        frame: 원본 프레임
        detections: 감지 결과 리스트

    Returns:
        np.ndarray: 바운딩박스가 그려진 프레임
    """
    result_frame = frame.copy()

    for detection in detections:
        x1, y1, x2, y2 = detection.bbox
        label = detection.label
        confidence = detection.confidence

        # 바운딩박스 색상 (클래스별)
        if label == "person":
            color = (0, 255, 0)  # 녹색
        elif label in ["car", "truck", "bus", "motorcycle"]:
            color = (255, 0, 0)  # 파란색
        else:
            color = (0, 255, 255)  # 노란색

        # 바운딩박스 그리기
        cv2.rectangle(result_frame, (x1, y1), (x2, y2), color, 2)

        # 라벨 텍스트
        label_text = f"{label}: {confidence:.2f}"
        text_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]

        # 라벨 배경
        cv2.rectangle(result_frame,
                     (x1, y1 - text_size[1] - 10),
                     (x1 + text_size[0], y1),
                     color, -1)

        # 라벨 텍스트
        cv2.putText(result_frame, label_text,
                   (x1, y1 - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                   (255, 255, 255), 2)

    return result_frame


def test_simple_ai_detector():
    """SimpleAIDetector 테스트 함수"""
    print("🧪 SimpleAIDetector 테스트 시작")

    try:
        with SimpleAIDetector() as detector:
            # 테스트 이미지 생성 (640x480 BGR)
            test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

            # 5초간 감지 테스트
            print("⏳ 5초간 감지 테스트...")
            for i in range(5):
                detections = detector.detect(test_frame)
                print(f"  {i+1}초: {len(detections)}개 객체 감지")

                for det in detections:
                    print(f"    - {det.label}: {det.confidence:.2f} at {det.bbox}")

                time.sleep(1)

            # 성능 통계
            stats = detector.get_stats()
            print(f"📊 성능 통계:")
            print(f"   - 총 프레임: {stats['total_frames']}")
            print(f"   - 총 감지: {stats['total_detections']}")
            print(f"   - 추론 시간: {stats['avg_inference_time_ms']:.1f}ms")
            print(f"   - 추론 FPS: {stats['inference_fps']:.1f}")
            print(f"   - NPU 사용률: {stats['npu_utilization']:.1f}%")

        print("✅ 테스트 완료")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")


if __name__ == "__main__":
    test_simple_ai_detector()