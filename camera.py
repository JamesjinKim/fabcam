from picamera2 import Picamera2
import cv2
import sys

try:
    picam2 = Picamera2()
except IndexError:
    print("카메라를 찾을 수 없습니다. 하드웨어 연결을 확인하세요.")
    sys.exit(1)

config = picam2.create_video_configuration({"format":"RGB888", "size":(1640,1232)})
picam2.configure(config)
picam2.start()

while True:
    img = picam2.capture_array()
    cv2.imshow("video", img)
    if cv2.waitKey(1) == ord('q'):
        break

picam2.stop()
cv2.destroyAllWindows()