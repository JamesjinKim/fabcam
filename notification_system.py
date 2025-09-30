#!/usr/bin/env python3
"""
간단한 이벤트 알림 시스템
AI 감지 결과에 따른 알림 및 이벤트 처리

Author: SHT Team
Date: 2025-09-28
"""

import time
import threading
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging
import json
from pathlib import Path

from simple_ai_detector import Detection

logger = logging.getLogger(__name__)


@dataclass
class NotificationEvent:
    """알림 이벤트"""
    event_id: str
    timestamp: float
    camera_id: int
    event_type: str  # "detection", "high_confidence", "new_object"
    detection: Detection
    message: str


class NotificationSystem:
    """
    이벤트 알림 시스템

    주요 기능:
    - AI 감지 결과 기반 알림 생성
    - 알림 쿨다운 및 중복 방지
    - 웹소켓을 통한 실시간 알림 전송
    - 이벤트 로그 저장
    """

    def __init__(self, config_manager=None):
        """
        Args:
            config_manager: 설정 관리자
        """
        self.config_manager = config_manager
        self.enabled = True
        self.min_confidence = 0.8
        self.cooldown_seconds = 10

        # 설정 로드
        self._load_config()

        # 알림 상태 관리
        self.recent_notifications = {}  # camera_id: {label: last_time}
        self.event_queue = []
        self.event_counter = 0

        # 스레드 안전성
        self._lock = threading.Lock()

        # 이벤트 로그 파일
        self.log_file = Path("events/detection_events.json")
        self.log_file.parent.mkdir(exist_ok=True)

        # 통계
        self.stats = {
            'total_events': 0,
            'notifications_sent': 0,
            'cooldown_blocks': 0,
            'last_event_time': 0
        }

        print(f"🔔 NotificationSystem 초기화 완료")
        print(f"   - 활성화: {self.enabled}")
        print(f"   - 최소 신뢰도: {self.min_confidence}")
        print(f"   - 쿨다운: {self.cooldown_seconds}초")

    def _load_config(self):
        """설정 로드"""
        if self.config_manager:
            self.enabled = self.config_manager.get('ai_detection.notification.enabled', True)
            self.min_confidence = self.config_manager.get('ai_detection.notification.min_confidence', 0.8)
            self.cooldown_seconds = self.config_manager.get('ai_detection.notification.cooldown_seconds', 10)

    def process_detections(self, detections: List[Detection], camera_id: int) -> List[NotificationEvent]:
        """
        감지 결과 처리 및 알림 이벤트 생성

        Args:
            detections: 감지된 객체 리스트
            camera_id: 카메라 ID

        Returns:
            List[NotificationEvent]: 생성된 알림 이벤트
        """
        if not self.enabled or not detections:
            return []

        events = []
        current_time = time.time()

        with self._lock:
            for detection in detections:
                # 신뢰도 필터링
                if detection.confidence < self.min_confidence:
                    continue

                # 쿨다운 체크
                camera_notifications = self.recent_notifications.get(camera_id, {})
                last_notification_time = camera_notifications.get(detection.label, 0)

                if current_time - last_notification_time < self.cooldown_seconds:
                    self.stats['cooldown_blocks'] += 1
                    continue

                # 알림 이벤트 생성
                event = self._create_notification_event(detection, camera_id, current_time)
                events.append(event)

                # 쿨다운 상태 업데이트
                if camera_id not in self.recent_notifications:
                    self.recent_notifications[camera_id] = {}
                self.recent_notifications[camera_id][detection.label] = current_time

                # 통계 업데이트
                self.stats['total_events'] += 1
                self.stats['notifications_sent'] += 1
                self.stats['last_event_time'] = current_time

                # 이벤트 로그 저장
                self._log_event(event)

                logger.info(f"[NOTIFY-CAM{camera_id}] {detection.label} 감지 알림: {detection.confidence:.2f}")

        return events

    def _create_notification_event(self, detection: Detection, camera_id: int, timestamp: float) -> NotificationEvent:
        """알림 이벤트 생성"""
        self.event_counter += 1
        event_id = f"evt_{camera_id}_{self.event_counter}_{int(timestamp)}"

        # 메시지 생성
        time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
        message = f"[{time_str}] 카메라 {camera_id}: {detection.label} 감지됨 (신뢰도: {detection.confidence:.1%})"

        return NotificationEvent(
            event_id=event_id,
            timestamp=timestamp,
            camera_id=camera_id,
            event_type="high_confidence",
            detection=detection,
            message=message
        )

    def _log_event(self, event: NotificationEvent):
        """이벤트 로그 저장"""
        try:
            # 기존 로그 로드
            events_log = []
            if self.log_file.exists():
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    events_log = json.load(f)

            # 새 이벤트 추가
            event_data = {
                'event_id': event.event_id,
                'timestamp': event.timestamp,
                'datetime': datetime.fromtimestamp(event.timestamp).isoformat(),
                'camera_id': event.camera_id,
                'event_type': event.event_type,
                'label': event.detection.label,
                'confidence': event.detection.confidence,
                'bbox': event.detection.bbox,
                'message': event.message
            }
            events_log.append(event_data)

            # 최근 100개 이벤트만 보관
            if len(events_log) > 100:
                events_log = events_log[-100:]

            # 로그 저장
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(events_log, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"[NOTIFY] 이벤트 로그 저장 오류: {e}")

    def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 이벤트 조회"""
        try:
            if not self.log_file.exists():
                return []

            with open(self.log_file, 'r', encoding='utf-8') as f:
                events_log = json.load(f)

            # 최신 순으로 정렬
            events_log.sort(key=lambda x: x['timestamp'], reverse=True)
            return events_log[:limit]

        except Exception as e:
            logger.error(f"[NOTIFY] 이벤트 조회 오류: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """알림 시스템 통계 반환"""
        with self._lock:
            return {
                'enabled': self.enabled,
                'total_events': self.stats['total_events'],
                'notifications_sent': self.stats['notifications_sent'],
                'cooldown_blocks': self.stats['cooldown_blocks'],
                'last_event_time': self.stats['last_event_time'],
                'min_confidence': self.min_confidence,
                'cooldown_seconds': self.cooldown_seconds,
                'active_cooldowns': {
                    camera_id: len(labels)
                    for camera_id, labels in self.recent_notifications.items()
                }
            }

    def clear_cooldowns(self):
        """쿨다운 상태 초기화"""
        with self._lock:
            self.recent_notifications.clear()
            logger.info("[NOTIFY] 쿨다운 상태 초기화됨")

    def set_enabled(self, enabled: bool):
        """알림 시스템 활성화/비활성화"""
        self.enabled = enabled
        logger.info(f"[NOTIFY] 알림 시스템 {'활성화' if enabled else '비활성화'}됨")

    def update_config(self, min_confidence: Optional[float] = None,
                     cooldown_seconds: Optional[int] = None):
        """설정 업데이트"""
        with self._lock:
            if min_confidence is not None:
                self.min_confidence = min_confidence
                logger.info(f"[NOTIFY] 최소 신뢰도 업데이트: {min_confidence}")

            if cooldown_seconds is not None:
                self.cooldown_seconds = cooldown_seconds
                logger.info(f"[NOTIFY] 쿨다운 시간 업데이트: {cooldown_seconds}초")


def test_notification_system():
    """NotificationSystem 테스트 함수"""
    print("🧪 NotificationSystem 테스트 시작")

    try:
        # 알림 시스템 초기화
        notifier = NotificationSystem()

        # 모의 감지 결과 생성
        test_detections = [
            Detection("person", 0.85, (100, 100, 200, 300), 0),
            Detection("car", 0.92, (300, 150, 500, 350), 2),
            Detection("person", 0.75, (150, 120, 250, 320), 0),  # 낮은 신뢰도
        ]

        print("\n🔍 감지 결과 처리 테스트...")

        # 첫 번째 처리
        events1 = notifier.process_detections(test_detections, camera_id=0)
        print(f"첫 번째 처리: {len(events1)}개 알림 생성")
        for event in events1:
            print(f"  - {event.message}")

        # 즉시 재처리 (쿨다운 테스트)
        events2 = notifier.process_detections(test_detections, camera_id=0)
        print(f"즉시 재처리: {len(events2)}개 알림 생성 (쿨다운으로 차단)")

        # 통계 확인
        stats = notifier.get_stats()
        print(f"\n📊 알림 시스템 통계:")
        print(f"   - 총 이벤트: {stats['total_events']}")
        print(f"   - 전송된 알림: {stats['notifications_sent']}")
        print(f"   - 쿨다운 차단: {stats['cooldown_blocks']}")

        # 최근 이벤트 조회
        recent_events = notifier.get_recent_events(5)
        print(f"\n📋 최근 이벤트 ({len(recent_events)}개):")
        for event in recent_events:
            print(f"   - {event['datetime']}: {event['message']}")

        print("\n✅ 테스트 완료")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")


if __name__ == "__main__":
    test_notification_system()