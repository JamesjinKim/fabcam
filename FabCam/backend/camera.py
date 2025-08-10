import cv2
import threading
import time
from datetime import datetime
import os

class CameraManager:
    def __init__(self, camera_index=0, width=640, height=480):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.camera = None
        self.is_streaming = False
        self.is_recording = False
        self.recording_thread = None
        self.video_writer = None
        self.current_frame = None
        self.lock = threading.Lock()
        
        # 저장 디렉토리 설정
        self.video_dir = "../static/videos"
        self.image_dir = "../static/images"
        os.makedirs(self.video_dir, exist_ok=True)
        os.makedirs(self.image_dir, exist_ok=True)
    
    def initialize_camera(self):
        try:
            # THSER102 + Pi Camera를 위한 다중 시도 방식
            camera_backends = [
                (cv2.CAP_V4L2, "V4L2"),
                (cv2.CAP_ANY, "ANY"),
                (cv2.CAP_GSTREAMER, "GStreamer")
            ]
            
            # 다양한 카메라 인덱스 시도 (THSER102는 다른 인덱스를 사용할 수 있음)
            for camera_idx in range(10):
                for backend, backend_name in camera_backends:
                    try:
                        print(f"카메라 시도: /dev/video{camera_idx} with {backend_name}")
                        self.camera = cv2.VideoCapture(camera_idx, backend)
                        
                        if self.camera.isOpened():
                            # 프레임 읽기 테스트
                            ret, frame = self.camera.read()
                            if ret and frame is not None:
                                print(f"✅ 카메라 연결 성공: /dev/video{camera_idx} ({backend_name})")
                                print(f"   해상도: {frame.shape[1]}x{frame.shape[0]}")
                                
                                # 카메라 설정
                                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                                self.camera.set(cv2.CAP_PROP_FPS, 30)
                                self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 버퍼 최소화
                                
                                return True
                            else:
                                print(f"❌ 프레임 읽기 실패: /dev/video{camera_idx}")
                        
                        self.camera.release()
                        self.camera = None
                        
                    except Exception as e:
                        print(f"❌ 카메라 {camera_idx} ({backend_name}) 오류: {e}")
                        if self.camera:
                            self.camera.release()
                            self.camera = None
                        continue
            
            print("❌ 모든 카메라 인덱스에서 초기화 실패")
            return False
            
        except Exception as e:
            print(f"Camera initialization error: {e}")
            return False
    
    def release_camera(self):
        if self.camera:
            self.camera.release()
            self.camera = None
    
    def start_streaming(self):
        if not self.camera and not self.initialize_camera():
            return False
        
        self.is_streaming = True
        return True
    
    def stop_streaming(self):
        self.is_streaming = False
        self.release_camera()
    
    def get_frame(self):
        if not self.camera or not self.is_streaming:
            return None
        
        with self.lock:
            ret, frame = self.camera.read()
            if ret:
                self.current_frame = frame.copy()
                return frame
            return None
    
    def generate_frames(self):
        while self.is_streaming:
            frame = self.get_frame()
            if frame is not None:
                # MJPEG 인코딩
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.1)  # 10 FPS
    
    def capture_image(self):
        if self.current_frame is not None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"snapshot_{timestamp}.jpg"
            filepath = os.path.join(self.image_dir, filename)
            
            with self.lock:
                cv2.imwrite(filepath, self.current_frame)
            
            return filename
        return None
    
    def start_recording(self):
        if self.is_recording:
            return False
        
        if not self.camera:
            return False
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}.avi"
        filepath = os.path.join(self.video_dir, filename)
        
        # 비디오 라이터 설정
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.video_writer = cv2.VideoWriter(filepath, fourcc, 20.0, (self.width, self.height))
        
        self.is_recording = True
        self.recording_thread = threading.Thread(target=self._record_video)
        self.recording_thread.start()
        
        return filename
    
    def stop_recording(self):
        if not self.is_recording:
            return False
        
        self.is_recording = False
        
        if self.recording_thread:
            self.recording_thread.join()
        
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        
        return True
    
    def _record_video(self):
        while self.is_recording:
            if self.current_frame is not None and self.video_writer:
                with self.lock:
                    self.video_writer.write(self.current_frame)
            time.sleep(1/20)  # 20 FPS
    
    def get_recording_status(self):
        return self.is_recording