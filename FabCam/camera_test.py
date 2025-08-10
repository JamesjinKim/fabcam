#!/usr/bin/env python3
"""
Pi Camera V2.1 직접 연결 테스트 스크립트
THSER102 없이 카메라가 제대로 작동하는지 확인
"""

import cv2
import time
import os
from datetime import datetime

def test_camera_detection():
    """카메라 하드웨어 인식 테스트"""
    print("=== Pi Camera V2.1 직접 연결 테스트 ===\n")
    print("1. 카메라 장치 검색 중...")
    
    # 사용 가능한 카메라 인덱스 찾기
    available_cameras = []
    for i in range(5):  # 0~4번 인덱스 검사
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"   ✅ /dev/video{i}: 카메라 발견! (해상도: {frame.shape[1]}x{frame.shape[0]})")
                available_cameras.append(i)
            else:
                print(f"   ❌ /dev/video{i}: 장치는 있으나 프레임 읽기 실패")
            cap.release()
        else:
            print(f"   ⚫ /dev/video{i}: 장치 없음")
    
    if not available_cameras:
        print("\n❌ 사용 가능한 카메라를 찾을 수 없습니다.")
        print("   해결 방법:")
        print("   1. 물리적 연결 상태 확인")
        print("   2. sudo vcgencmd get_camera 실행")
        print("   3. /boot/config.txt에서 camera_auto_detect=1 확인")
        return None
    
    print(f"\n✅ 총 {len(available_cameras)}개 카메라 발견!")
    return available_cameras[0]  # 첫 번째 카메라 사용

def test_camera_capture(camera_index):
    """카메라 영상 취득 및 저장 테스트"""
    print(f"\n2. 카메라 {camera_index}번으로 영상 취득 테스트...")
    
    # 카메라 초기화
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("❌ 카메라 초기화 실패!")
        return False
    
    # 카메라 설정 - V2.1 최적화
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    print("   카메라 설정 완료 (640x480, 30fps)")
    
    # 테스트 이미지 저장 디렉토리 생성
    os.makedirs("test_images", exist_ok=True)
    
    print("   5초 동안 프레임 취득 테스트...")
    frame_count = 0
    start_time = time.time()
    
    try:
        while time.time() - start_time < 5:
            ret, frame = cap.read()
            if ret and frame is not None:
                frame_count += 1
                # 1초마다 스냅샷 저장
                if frame_count % 30 == 0:  # 30fps 기준 1초마다
                    timestamp = datetime.now().strftime("%H%M%S")
                    filename = f"test_images/snapshot_{timestamp}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"   📸 스냅샷 저장: {filename}")
            else:
                print("   ⚠️ 프레임 읽기 실패")
                break
            
            time.sleep(0.033)  # ~30fps
    
    except KeyboardInterrupt:
        print("\n   ⏹️ 사용자가 테스트를 중단했습니다.")
    
    finally:
        cap.release()
    
    print(f"\n   ✅ 테스트 완료: 총 {frame_count}개 프레임 취득")
    print(f"   평균 FPS: {frame_count / 5:.1f}")
    
    return frame_count > 0

def test_camera_info(camera_index):
    """카메라 상세 정보 출력"""
    print(f"\n3. 카메라 {camera_index}번 상세 정보...")
    
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("❌ 카메라 접근 실패!")
        return
    
    # 카메라 속성 정보
    properties = {
        'WIDTH': cv2.CAP_PROP_FRAME_WIDTH,
        'HEIGHT': cv2.CAP_PROP_FRAME_HEIGHT,
        'FPS': cv2.CAP_PROP_FPS,
        'BRIGHTNESS': cv2.CAP_PROP_BRIGHTNESS,
        'CONTRAST': cv2.CAP_PROP_CONTRAST,
        'SATURATION': cv2.CAP_PROP_SATURATION,
        'EXPOSURE': cv2.CAP_PROP_EXPOSURE,
    }
    
    print("   카메라 속성:")
    for name, prop in properties.items():
        try:
            value = cap.get(prop)
            print(f"   - {name}: {value}")
        except:
            print(f"   - {name}: 지원 안함")
    
    cap.release()

def main():
    """메인 테스트 실행"""
    try:
        # 1. 카메라 검색
        camera_index = test_camera_detection()
        if camera_index is None:
            return
        
        # 2. 영상 취득 테스트
        success = test_camera_capture(camera_index)
        if not success:
            print("❌ 영상 취득 테스트 실패!")
            return
        
        # 3. 카메라 정보 출력
        test_camera_info(camera_index)
        
        print("\n🎉 모든 테스트 완료!")
        print("   - test_images/ 폴더에서 저장된 이미지 확인 가능")
        print("   - 카메라가 정상적으로 작동합니다!")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        print("   디버깅을 위해 다음 명령어를 실행해보세요:")
        print("   - vcgencmd get_camera")
        print("   - v4l2-ctl --list-devices")
        print("   - lsmod | grep bcm2835")

if __name__ == "__main__":
    main()