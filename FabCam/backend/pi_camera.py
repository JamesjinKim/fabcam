import subprocess
import os
import time
import threading
from datetime import datetime

class PiCameraManager:
    """Raspberry Pi Camera Manager using rpicam-apps"""
    
    def __init__(self, camera_index=0, width=640, height=480):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.is_streaming = False
        self.is_recording = False
        self.stream_process = None
        self.record_process = None
        
        self.video_dir = "../static/videos"
        self.image_dir = "../static/images"
        os.makedirs(self.video_dir, exist_ok=True)
        os.makedirs(self.image_dir, exist_ok=True)
    
    def test_camera(self):
        """카메라 테스트"""
        try:
            result = subprocess.run(
                ["rpicam-hello", "--list-cameras"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("✅ 카메라 감지됨:")
                print(result.stdout)
                return True
            else:
                print("❌ 카메라 감지 실패")
                return False
        except Exception as e:
            print(f"❌ 카메라 테스트 오류: {e}")
            return False
    
    def start_mjpeg_stream(self, port=8081):
        """MJPEG 스트림 시작"""
        if self.is_streaming:
            return False
        
        try:
            cmd = [
                "rpicam-vid",
                "--camera", str(self.camera_index),
                "--width", str(self.width),
                "--height", str(self.height),
                "--framerate", "10",
                "--timeout", "0",  # 무한 스트리밍
                "--codec", "mjpeg",
                "--listen",  # HTTP 서버 모드
                "-o", f"tcp://0.0.0.0:{port}"
            ]
            
            self.stream_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.is_streaming = True
            print(f"✅ MJPEG 스트림 시작됨 - http://localhost:{port}/stream")
            return True
            
        except Exception as e:
            print(f"❌ 스트림 시작 실패: {e}")
            return False
    
    def stop_stream(self):
        """스트림 중지"""
        if self.stream_process:
            self.stream_process.terminate()
            self.stream_process.wait(timeout=5)
            self.stream_process = None
            self.is_streaming = False
            print("✅ 스트림 중지됨")
            return True
        return False
    
    def capture_image(self):
        """스냅샷 캡처"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"snapshot_{timestamp}.jpg"
            filepath = os.path.join(self.image_dir, filename)
            
            cmd = [
                "rpicam-jpeg",
                "--camera", str(self.camera_index),
                "--width", str(self.width),
                "--height", str(self.height),
                "-o", filepath,
                "-t", "100"  # 100ms 후 캡처
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and os.path.exists(filepath):
                print(f"✅ 이미지 캡처됨: {filename}")
                return filename
            else:
                print(f"❌ 이미지 캡처 실패")
                return None
                
        except Exception as e:
            print(f"❌ 캡처 오류: {e}")
            return None
    
    def start_recording(self):
        """녹화 시작"""
        if self.is_recording:
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.h264"
            filepath = os.path.join(self.video_dir, filename)
            
            cmd = [
                "rpicam-vid",
                "--camera", str(self.camera_index),
                "--width", str(self.width),
                "--height", str(self.height),
                "--framerate", "25",
                "--timeout", "0",  # 무한 녹화
                "-o", filepath
            ]
            
            self.record_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.is_recording = True
            self.current_recording = filename
            print(f"✅ 녹화 시작됨: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ 녹화 시작 실패: {e}")
            return None
    
    def stop_recording(self):
        """녹화 중지"""
        if not self.is_recording:
            return False
        
        if self.record_process:
            self.record_process.terminate()
            self.record_process.wait(timeout=5)
            self.record_process = None
            self.is_recording = False
            
            # H264를 MP4로 변환 (선택사항)
            if hasattr(self, 'current_recording'):
                self.convert_to_mp4(self.current_recording)
            
            print("✅ 녹화 중지됨")
            return True
        return False
    
    def convert_to_mp4(self, h264_filename):
        """H264를 MP4로 변환"""
        try:
            h264_path = os.path.join(self.video_dir, h264_filename)
            mp4_filename = h264_filename.replace('.h264', '.mp4')
            mp4_path = os.path.join(self.video_dir, mp4_filename)
            
            cmd = [
                "ffmpeg",
                "-i", h264_path,
                "-c:v", "copy",
                mp4_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                os.remove(h264_path)  # 원본 H264 파일 삭제
                print(f"✅ MP4 변환 완료: {mp4_filename}")
                return mp4_filename
                
        except Exception as e:
            print(f"⚠️ MP4 변환 실패 (ffmpeg 필요): {e}")
        
        return h264_filename
    
    def get_status(self):
        """상태 확인"""
        return {
            "is_streaming": self.is_streaming,
            "is_recording": self.is_recording,
            "camera_index": self.camera_index,
            "resolution": f"{self.width}x{self.height}"
        }

if __name__ == "__main__":
    cam = PiCameraManager()
    
    print("🎥 Raspberry Pi 카메라 매니저 테스트")
    
    if cam.test_camera():
        print("\n📸 이미지 캡처 테스트...")
        image = cam.capture_image()
        if image:
            print(f"   저장됨: {image}")
        
        print("\n📹 스트림 테스트...")
        if cam.start_mjpeg_stream():
            print("   5초 동안 스트리밍...")
            time.sleep(5)
            cam.stop_stream()
        
        print("\n🎬 녹화 테스트...")
        recording = cam.start_recording()
        if recording:
            print("   5초 동안 녹화...")
            time.sleep(5)
            cam.stop_recording()