#!/usr/bin/env python3
"""
MediaPipe 기반 손 감지 엔진
실시간 손 감지 및 추적 전용 모듈

Author: SHT Team
Date: 2025-09-29
"""

import cv2
import numpy as np
import time
import threading
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import logging

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    print("⚠️ MediaPipe가 설치되지 않음. 설치: pip install mediapipe")
    MEDIAPIPE_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class HandDetection:
    """손 감지 결과"""
    label: str  # "Left Hand" or "Right Hand"
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    landmarks: List[Tuple[float, float]]  # 21개 랜드마크 좌표
    handedness: str  # LEFT or RIGHT


class HandDetector:
    """MediaPipe 기반 손 감지기"""

    def __init__(self,
                 min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5,
                 max_num_hands: int = 2):
        """
        초기화

        Args:
            min_detection_confidence: 최소 감지 신뢰도
            min_tracking_confidence: 최소 추적 신뢰도
            max_num_hands: 최대 감지 손 개수
        """
        if not MEDIAPIPE_AVAILABLE:
            raise ImportError("MediaPipe가 필요합니다. 설치: pip install mediapipe")

        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils

        # MediaPipe 손 감지기 초기화
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,  # 비디오 스트림 모드
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

        # 통계
        self.stats = {
            'total_detections': 0,
            'frames_processed': 0,
            'avg_processing_time': 0,
            'last_detection_time': 0
        }

        self.processing_times = []
        self.stats_lock = threading.Lock()

        logger.info(f"[HandDetector] 초기화 완료 (최대 {max_num_hands}개 손 감지)")

    def detect(self, frame: np.ndarray) -> List[HandDetection]:
        """
        프레임에서 손 감지

        Args:
            frame: BGR 이미지 프레임

        Returns:
            HandDetection 리스트
        """
        start_time = time.time()
        detections = []

        # BGR을 RGB로 변환
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # MediaPipe 손 감지 실행
        results = self.hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            h, w, _ = frame.shape

            for idx, (hand_landmarks, handedness) in enumerate(
                zip(results.multi_hand_landmarks, results.multi_handedness)
            ):
                # 손 바운딩 박스 계산
                x_coords = [landmark.x * w for landmark in hand_landmarks.landmark]
                y_coords = [landmark.y * h for landmark in hand_landmarks.landmark]

                x1 = max(0, int(min(x_coords) - 20))
                y1 = max(0, int(min(y_coords) - 20))
                x2 = min(w, int(max(x_coords) + 20))
                y2 = min(h, int(max(y_coords) + 20))

                # 랜드마크 좌표 추출
                landmarks = [(lm.x * w, lm.y * h) for lm in hand_landmarks.landmark]

                # 손 방향 (LEFT/RIGHT)
                hand_label = handedness.classification[0].label
                confidence = handedness.classification[0].score

                # 감지 결과 생성
                detection = HandDetection(
                    label=f"{hand_label} Hand",
                    confidence=confidence,
                    bbox=(x1, y1, x2, y2),
                    landmarks=landmarks,
                    handedness=hand_label
                )

                detections.append(detection)

        # 통계 업데이트
        processing_time = time.time() - start_time
        with self.stats_lock:
            self.stats['frames_processed'] += 1
            self.stats['total_detections'] += len(detections)
            if detections:
                self.stats['last_detection_time'] = time.time()

            self.processing_times.append(processing_time)
            if len(self.processing_times) > 100:
                self.processing_times.pop(0)
            self.stats['avg_processing_time'] = np.mean(self.processing_times)

        return detections

    def draw_detections(self, frame: np.ndarray, detections: List[HandDetection]) -> np.ndarray:
        """
        프레임에 감지 결과 그리기

        Args:
            frame: BGR 이미지 프레임
            detections: 감지 결과 리스트

        Returns:
            그려진 프레임
        """
        for detection in detections:
            x1, y1, x2, y2 = detection.bbox

            # 바운딩 박스 그리기
            color = (0, 255, 0) if detection.handedness == "Right" else (255, 0, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # 라벨 그리기
            label = f"{detection.label}: {detection.confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]

            cv2.rectangle(frame, (x1, y1 - label_size[1] - 10),
                         (x1 + label_size[0], y1), color, -1)
            cv2.putText(frame, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

            # 손가락 관절 그리기 (선택사항)
            if len(detection.landmarks) == 21:  # MediaPipe는 21개 랜드마크 제공
                for i, (x, y) in enumerate(detection.landmarks):
                    cv2.circle(frame, (int(x), int(y)), 3, (0, 255, 255), -1)

        return frame

    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        with self.stats_lock:
            return self.stats.copy()

    def close(self):
        """리소스 정리"""
        if hasattr(self, 'hands'):
            self.hands.close()
        logger.info("[HandDetector] 종료됨")


class HandDetectorHailo:
    """
    Hailo NPU용 손 감지기 (YOLOv8-pose 기반)
    Note: Hailo Model Zoo에서 yolov8n_pose.hef 모델 필요
    """

    def __init__(self, model_path: str = "models/yolov8n_pose.hef",
                 confidence_threshold: float = 0.5):
        """
        Hailo 기반 포즈 감지로 손 위치 추정
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold

        # 여기에 Hailo 초기화 코드 추가
        logger.info("[HandDetectorHailo] 초기화 (Pose 기반 손 감지)")

    def detect_from_pose(self, frame: np.ndarray) -> List[HandDetection]:
        """
        포즈 키포인트에서 손목/손 위치 추출
        COCO Pose 키포인트:
        - 9: 왼쪽 손목
        - 10: 오른쪽 손목
        """
        # TODO: Hailo pose 모델 추론 구현
        return []


if __name__ == "__main__":
    # 테스트 코드
    import sys

    print("손 감지 테스트 시작...")

    # MediaPipe 손 감지기 생성
    detector = HandDetector(
        min_detection_confidence=0.5,
        max_num_hands=2
    )

    # 웹캠 열기
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 손 감지
        detections = detector.detect(frame)

        # 결과 그리기
        frame = detector.draw_detections(frame, detections)

        # 통계 표시
        stats = detector.get_stats()
        info_text = f"FPS: {1/stats['avg_processing_time']:.1f} | Hands: {len(detections)}"
        cv2.putText(frame, info_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # 화면 표시
        cv2.imshow("Hand Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    detector.close()

    print("\n통계:")
    print(f"- 처리된 프레임: {stats['frames_processed']}")
    print(f"- 총 감지 수: {stats['total_detections']}")
    print(f"- 평균 처리 시간: {stats['avg_processing_time']*1000:.1f}ms")