#!/usr/bin/env python3
"""
Raspberry Pi Camera Test Script
Tests both libcamera (via picamera2) and OpenCV methods
"""

import sys
import time
import cv2
import numpy as np

def test_opencv_camera(index=0):
    """OpenCV를 사용한 카메라 테스트"""
    print(f"\n=== OpenCV 카메라 테스트 (인덱스: {index}) ===")
    
    backends = [
        (cv2.CAP_V4L2, "V4L2"),
        (cv2.CAP_ANY, "ANY"),
    ]
    
    for backend, backend_name in backends:
        print(f"\n백엔드 시도: {backend_name}")
        cap = cv2.VideoCapture(index, backend)
        
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"✅ 성공! 해상도: {frame.shape[1]}x{frame.shape[0]}")
                
                # 이미지 저장
                filename = f"opencv_test_cam{index}_{backend_name}.jpg"
                cv2.imwrite(filename, frame)
                print(f"   저장됨: {filename}")
                
                cap.release()
                return True
            else:
                print(f"❌ 프레임 읽기 실패")
        else:
            print(f"❌ 카메라 열기 실패")
        
        cap.release()
    
    return False

def test_picamera2():
    """picamera2를 사용한 카메라 테스트"""
    print("\n=== Picamera2 테스트 ===")
    try:
        from picamera2 import Picamera2
        
        # 사용 가능한 카메라 목록
        cameras = Picamera2.global_camera_info()
        print(f"감지된 카메라 수: {len(cameras)}")
        
        for i, cam_info in enumerate(cameras):
            print(f"\n카메라 {i}: {cam_info}")
            
            try:
                picam2 = Picamera2(camera_num=i)
                config = picam2.create_still_configuration(
                    main={"size": (640, 480)}
                )
                picam2.configure(config)
                picam2.start()
                
                # 캡처
                array = picam2.capture_array()
                print(f"✅ 캡처 성공! Shape: {array.shape}")
                
                # 저장
                filename = f"picamera2_test_cam{i}.jpg"
                cv2.imwrite(filename, cv2.cvtColor(array, cv2.COLOR_RGB2BGR))
                print(f"   저장됨: {filename}")
                
                picam2.stop()
                picam2.close()
                
            except Exception as e:
                print(f"❌ 카메라 {i} 오류: {e}")
        
        return True
        
    except ImportError:
        print("❌ picamera2가 설치되지 않음")
        print("   설치: sudo apt install -y python3-picamera2")
        return False
    except Exception as e:
        print(f"❌ Picamera2 오류: {e}")
        return False

def main():
    print("=== Raspberry Pi 카메라 테스트 시작 ===")
    print("시스템 정보:")
    print(f"  Python: {sys.version}")
    print(f"  OpenCV: {cv2.__version__}")
    
    # Picamera2 테스트
    picamera_ok = test_picamera2()
    
    # OpenCV 테스트 - 여러 인덱스 시도
    opencv_ok = False
    for idx in range(10):
        if test_opencv_camera(idx):
            opencv_ok = True
            break
    
    # 결과 요약
    print("\n=== 테스트 결과 요약 ===")
    print(f"Picamera2: {'✅ 성공' if picamera_ok else '❌ 실패'}")
    print(f"OpenCV: {'✅ 성공' if opencv_ok else '❌ 실패'}")
    
    if not picamera_ok and not opencv_ok:
        print("\n⚠️  모든 테스트 실패!")
        print("권장 사항:")
        print("1. sudo raspi-config로 카메라 활성화 확인")
        print("2. sudo apt update && sudo apt install -y python3-picamera2")
        print("3. 카메라 연결 상태 확인")
    
    return 0 if (picamera_ok or opencv_ok) else 1

if __name__ == "__main__":
    sys.exit(main())