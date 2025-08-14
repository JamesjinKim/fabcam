import cv2
import threading
import time
from datetime import datetime
import os
from abc import ABC, abstractmethod
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
    print("✅ Picamera2 라이브러리 사용 가능")
except ImportError:
    PICAMERA2_AVAILABLE = False
    print("⚠️ Picamera2 사용 불가, OpenCV fallback 사용")

class CameraBase(ABC):
    def __init__(self, camera_index, camera_name, width=640, height=480):
        self.camera_index = camera_index
        self.camera_name = camera_name
        self.width = width
        self.height = height
        self.camera = None
        self.picam2 = None
        self.use_picamera2 = PICAMERA2_AVAILABLE
        self.is_streaming = False
        self.is_recording = False
        self.recording_thread = None
        self.video_writer = None
        self.current_frame = None
        self.lock = threading.Lock()
        
        # HD 모드 설정
        self.is_hd_mode = False
        self.hd_width = 1280
        self.hd_height = 720
        
        # 저장 디렉토리 설정
        self.video_dir = f"../static/videos/{camera_name}"
        self.image_dir = f"../static/images/{camera_name}"
        os.makedirs(self.video_dir, exist_ok=True)
        os.makedirs(self.image_dir, exist_ok=True)
    
    def initialize_camera(self):
        """Picamera2 전용 카메라 초기화 (라즈베리파이 카메라 모듈용)"""
        print(f"🔍 {self.camera_name} 초기화 시작 (Picamera2 전용)")
        
        # 비활성화된 카메라 인덱스 처리
        if self.camera_index < 0:
            print(f"⏭️ {self.camera_name}는 비활성화되어 있습니다.")
            return False
        
        try:
            # 카메라 감지 확인
            print("📷 사용 가능한 카메라 확인...")
            cameras = Picamera2.global_camera_info()
            if len(cameras) == 0:
                print("❌ 카메라를 찾을 수 없습니다")
                return False
            
            if self.camera_index >= len(cameras):
                print(f"❌ {self.camera_name}를 찾을 수 없습니다 (사용 가능: {len(cameras)}개)")
                return False
            
            print(f"✅ {len(cameras)}개 카메라 감지됨:")
            for i, cam in enumerate(cameras):
                print(f"   📷 카메라 {i}: {cam.get('Model', 'Unknown')}")
            
            # Picamera2 객체 생성 및 설정
            print(f"🎥 {self.camera_name} Picamera2 초기화...")
            self.picam2 = Picamera2(self.camera_index)
            
            # 웹 스트리밍 최적화 설정
            config = self.picam2.create_video_configuration(
                main={"format": "RGB888", "size": (self.width, self.height)},
                controls={"FrameRate": 30}
            )
            print(f"📐 {self.camera_name} 설정: {self.width}x{self.height} RGB888")
            
            # 설정 적용 및 시작
            self.picam2.configure(config)
            self.picam2.start()
            
            # 카메라 안정화 대기
            print(f"⏱️  {self.camera_name} 안정화 대기 중...")
            time.sleep(2)
            
            # 테스트 프레임 캡처
            print(f"🧪 {self.camera_name} 프레임 캡처 테스트...")
            frame = self.picam2.capture_array()
            
            if frame is None or frame.size == 0:
                print(f"❌ {self.camera_name} 프레임 캡처 실패")
                self.picam2.stop()
                self.picam2.close()
                self.picam2 = None
                return False
            
            # RGBA → RGB 변환 (Picamera2는 RGBA로 출력)
            original_shape = frame.shape
            if len(frame.shape) == 3 and frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
                print(f"🔄 RGBA → RGB 변환: {original_shape} → {frame.shape}")
            
            print(f"✅ {self.camera_name} 초기화 완료!")
            print(f"   📏 해상도: {frame.shape[1]}x{frame.shape[0]}")
            print(f"   💾 프레임 크기: {frame.size} bytes")
            
            self.current_frame = frame.copy()
            self.use_picamera2 = True
            return True
            
        except Exception as e:
            print(f"❌ {self.camera_name} 초기화 실패: {e}")
            if hasattr(self, 'picam2') and self.picam2:
                try:
                    self.picam2.stop()
                    self.picam2.close()
                except:
                    pass
                self.picam2 = None
            self.use_picamera2 = False
            return False
    
    def release_camera(self):
        try:
            if self.use_picamera2 and self.picam2:
                try:
                    self.picam2.stop()
                    self.picam2.close()
                    print(f"{self.camera_name} Picamera2 resources released")
                except Exception as e:
                    print(f"Error releasing {self.camera_name} Picamera2: {e}")
                finally:
                    self.picam2 = None
            
            if self.camera:
                try:
                    self.camera.release()
                    print(f"{self.camera_name} OpenCV camera resources released")
                except Exception as e:
                    print(f"Error releasing {self.camera_name} OpenCV camera: {e}")
                finally:
                    self.camera = None
        except Exception as e:
            print(f"Error during {self.camera_name} release: {e}")
    
    def start_streaming(self):
        if not self.camera and not self.picam2 and not self.initialize_camera():
            return False
        
        self.is_streaming = True
        print(f"🎬 {self.camera_name} 스트리밍 시작")
        return True
    
    def stop_streaming(self):
        try:
            self.is_streaming = False
            # 녹화도 함께 중단
            if self.is_recording:
                self.stop_recording()
            self.release_camera()
            print(f"🛑 {self.camera_name} 스트리밍 중지")
        except Exception as e:
            print(f"Error stopping {self.camera_name} streaming: {e}")
    
    def get_frame(self):
        if not self.is_streaming:
            return None
        
        with self.lock:
            if self.use_picamera2 and self.picam2:
                try:
                    frame = self.picam2.capture_array()
                    if frame is not None:
                        # RGBA를 RGB로 변환 (OpenCV 호환성을 위해)
                        if len(frame.shape) == 3 and frame.shape[2] == 4:
                            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
                        
                        # 영상 반전 (상하좌우)
                        frame = cv2.flip(frame, 1)
                        
                        self.current_frame = frame.copy()
                        return frame
                except Exception as e:
                    print(f"{self.camera_name} Picamera2 프레임 캡처 오류: {e}")
                    return None
            elif self.camera:
                ret, frame = self.camera.read()
                if ret:
                    self.current_frame = frame.copy()
                    return frame
            
            return None
    
    def generate_frames(self):
        frame_count = 0
        fps_counter = 0
        fps_start_time = time.time()
        try:
            while self.is_streaming:
                try:
                    frame = self.get_frame()
                    if frame is not None:
                        # HD 모드에 따른 MJPEG 인코딩 최적화
                        if self.is_hd_mode:
                            encode_params = [
                                cv2.IMWRITE_JPEG_QUALITY, 95,
                                cv2.IMWRITE_JPEG_OPTIMIZE, 1,
                                cv2.IMWRITE_JPEG_PROGRESSIVE, 1
                            ]
                            mode_prefix = "HD"
                        else:
                            encode_params = [
                                cv2.IMWRITE_JPEG_QUALITY, 85,
                                cv2.IMWRITE_JPEG_OPTIMIZE, 1,
                                cv2.IMWRITE_JPEG_PROGRESSIVE, 1
                            ]
                            mode_prefix = "일반"
                        
                        ret, buffer = cv2.imencode('.jpg', frame, encode_params)
                        if ret:
                            frame_data = (b'--frame\r\n'
                                         b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                            yield frame_data
                            frame_count += 1
                            fps_counter += 1
                            
                            # FPS 모니터링 (10초마다)
                            if fps_counter >= 300:
                                current_time = time.time()
                                actual_fps = fps_counter / (current_time - fps_start_time)
                                resolution = f"{self.hd_width}x{self.hd_height}" if self.is_hd_mode else f"{self.width}x{self.height}"
                                print(f"📊 {self.camera_name} {mode_prefix} 스트리밍 FPS: {actual_fps:.1f} ({resolution})")
                                fps_counter = 0
                                fps_start_time = current_time
                    
                    time.sleep(0.033)  # ~30 FPS
                    
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                    print(f"{self.camera_name} Client disconnected from video stream")
                    break
                except Exception as e:
                    print(f"{self.camera_name} Frame generation error: {e}")
                    if not self.is_streaming:
                        break
                    time.sleep(0.1)
                    
        except GeneratorExit:
            print(f"{self.camera_name} Video stream generator exited")
        except Exception as e:
            print(f"{self.camera_name} Video stream error: {e}")
        finally:
            mode_info = "HD" if self.is_hd_mode else "일반"
            print(f"{self.camera_name} {mode_info} 비디오 프레임 생성 중지 (생성된 프레임: {frame_count}개)")
    
    def capture_image(self):
        if self.current_frame is not None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"snapshot_{self.camera_name}_{timestamp}.jpg"
            filepath = os.path.join(self.image_dir, filename)
            
            with self.lock:
                cv2.imwrite(filepath, self.current_frame)
            
            print(f"📸 {self.camera_name} 스냅샷 저장: {filename}")
            return filename
        return None
    
    def start_recording(self):
        if self.is_recording:
            return False
        
        if not self.camera and not self.picam2:
            return False
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{self.camera_name}_{timestamp}.mp4"
        filepath = os.path.join(self.video_dir, filename)
        
        # 비디오 라이터 설정 (MP4 포맷)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(filepath, fourcc, 20.0, (self.width, self.height))
        
        self.is_recording = True
        self.recording_thread = threading.Thread(target=self._record_video)
        self.recording_thread.start()
        
        print(f"🔴 {self.camera_name} 녹화 시작: {filename}")
        return filename
    
    def stop_recording(self):
        if not self.is_recording:
            return False
        
        try:
            self.is_recording = False
            
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=3.0)
                if self.recording_thread.is_alive():
                    print(f"Warning: {self.camera_name} recording thread did not stop gracefully")
            
            if self.video_writer:
                try:
                    self.video_writer.release()
                    print(f"⏹️ {self.camera_name} 녹화 중지 - Video writer released successfully")
                except Exception as e:
                    print(f"Error releasing {self.camera_name} video writer: {e}")
                finally:
                    self.video_writer = None
            
            return True
        except Exception as e:
            print(f"Error stopping {self.camera_name} recording: {e}")
            return False
    
    def _record_video(self):
        while self.is_recording:
            if self.current_frame is not None and self.video_writer:
                with self.lock:
                    self.video_writer.write(self.current_frame)
            time.sleep(1/20)  # 20 FPS
    
    def get_recording_status(self):
        return self.is_recording
    
    def switch_to_hd_mode(self):
        """HD 모드로 전환 (1280x720@25fps)"""
        if self.is_hd_mode:
            return True
            
        print(f"🎥 {self.camera_name} HD 모드로 전환 중... (1280x720@25fps)")
        
        with self.lock:
            try:
                if self.use_picamera2 and self.picam2:
                    was_streaming = self.is_streaming
                    if was_streaming:
                        self.is_streaming = False
                        time.sleep(0.5)
                    
                    hd_config = self.picam2.create_video_configuration(
                        main={"format": "RGB888", "size": (self.hd_width, self.hd_height)},
                        controls={"FrameRate": 25}
                    )
                    
                    self.picam2.stop()
                    time.sleep(0.5)
                    self.picam2.configure(hd_config)
                    self.picam2.start()
                    
                    time.sleep(3)
                    
                    test_frame = self.picam2.capture_array()
                    if test_frame is not None and test_frame.size > 0:
                        self.is_hd_mode = True
                        print(f"✅ {self.camera_name} HD 모드 전환 완료: {test_frame.shape[1]}x{test_frame.shape[0]}")
                        
                        if was_streaming:
                            self.is_streaming = True
                        return True
                    else:
                        print(f"❌ {self.camera_name} HD 모드 전환 실패: 프레임 캡처 불가")
                        return False
                        
            except Exception as e:
                print(f"❌ {self.camera_name} HD 모드 전환 오류: {e}")
                self.is_hd_mode = False
                return False
        
        return False
    
    def switch_to_normal_mode(self):
        """일반 모드로 전환 (640x480@30fps)"""
        if not self.is_hd_mode:
            return True
            
        print(f"📺 {self.camera_name} 일반 모드로 전환 중... (640x480@30fps)")
        
        with self.lock:
            try:
                if self.use_picamera2 and self.picam2:
                    was_streaming = self.is_streaming
                    if was_streaming:
                        self.is_streaming = False
                        time.sleep(0.5)
                    
                    normal_config = self.picam2.create_video_configuration(
                        main={"format": "RGB888", "size": (self.width, self.height)},
                        controls={"FrameRate": 30}
                    )
                    
                    self.picam2.stop()
                    self.picam2.configure(normal_config)
                    self.picam2.start()
                    
                    time.sleep(2)
                    
                    test_frame = self.picam2.capture_array()
                    if test_frame is not None and test_frame.size > 0:
                        self.is_hd_mode = False
                        print(f"✅ {self.camera_name} 일반 모드 전환 완료: {test_frame.shape[1]}x{test_frame.shape[0]}")
                        
                        if was_streaming:
                            self.is_streaming = True
                        return True
                    else:
                        print(f"❌ {self.camera_name} 일반 모드 전환 실패: 프레임 캡처 불가")
                        return False
                        
            except Exception as e:
                print(f"❌ {self.camera_name} 일반 모드 전환 오류: {e}")
                return False
        
        return False