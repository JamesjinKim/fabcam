#!/bin/bash

echo "🔍 THSER102 + Pi Camera 연결 테스트 시작..."

echo ""
echo "1️⃣ 하드웨어 상태 확인"
echo "📱 USB 장치 목록:"
lsusb

echo ""
echo "📹 비디오 장치 목록:"
ls -la /dev/video* 2>/dev/null || echo "❌ /dev/video* 장치 없음"

echo ""
echo "2️⃣ 카메라 감지 상태"
echo "📸 VideoCore 카메라 상태:"
vcgencmd get_camera

echo ""
echo "3️⃣ libcamera 카메라 목록"
echo "📷 libcamera 감지된 카메라:"
libcamera-hello --list-cameras 2>/dev/null || echo "❌ libcamera로 카메라 감지 안됨"

echo ""
echo "4️⃣ V4L2 장치 상태"
echo "📺 V4L2 장치 목록:"
v4l2-ctl --list-devices 2>/dev/null || echo "❌ V4L2 장치 없음"

echo ""
echo "5️⃣ 최근 시스템 로그"
echo "📋 카메라/비디오 관련 최근 로그:"
dmesg | grep -i -E "camera|video|thser|thine" | tail -10

echo ""
echo "6️⃣ OpenCV 카메라 테스트"
echo "🐍 Python OpenCV로 카메라 접근 테스트:"
python3 -c "
import cv2
import sys

# 다양한 카메라 인덱스 테스트
for i in range(5):
    print(f'  📹 /dev/video{i} 테스트 중...', end='')
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f' ✅ 성공! 해상도: {frame.shape[1]}x{frame.shape[0]}')
            cap.release()
            sys.exit(0)
        else:
            print(' ❌ 프레임 읽기 실패')
    else:
        print(' ❌ 열기 실패')
    cap.release()

print('❌ 모든 카메라 인덱스에서 접근 실패')
"

echo ""
echo "🔧 **해결 방안 제안:**"
echo ""
echo "✅ **하드웨어 연결 재확인:**"
echo "   1. 전원 완전 차단 후 재연결"
echo "   2. Rx 보드 GPIO 핀 완전 삽입 확인"
echo "   3. 3개 나사로 Rx 보드 완전 고정"
echo "   4. Ethernet 케이블 Rx-Tx 간 연결 확인"
echo "   5. 카메라-Tx 보드 간 FFC 케이블 확인"
echo ""
echo "🔄 **시스템 재부팅 필요:**"
echo "   sudo reboot"
echo ""
echo "📞 **추가 지원이 필요하면:**"
echo "   - THSER102 공식 가이드: https://www.thinesolutions.com/thser102/start-guide"
echo "   - 카메라 모듈 호환성 확인 (V1.3/V2/HQ/V3)"