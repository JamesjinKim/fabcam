"""
동적 카메라 전환을 지원하는 카메라 팩토리
"""
import subprocess
from camera import CameraManager
from pi_camera import PiCameraManager

class CameraFactory:
    """카메라 자동 감지 및 전환"""
    
    @staticmethod
    def detect_pi_camera():
        """Raspberry Pi 카메라 감지"""
        try:
            result = subprocess.run(
                ["rpicam-hello", "--list-cameras"],
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.returncode == 0 and "Available cameras" in result.stdout
        except:
            return False
    
    @staticmethod
    def detect_usb_camera():
        """USB 카메라 감지"""
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                ret, _ = cap.read()
                cap.release()
                return ret
            return False
        except:
            return False
    
    @staticmethod
    def create_camera(prefer_pi=True):
        """
        카메라 인스턴스 생성
        prefer_pi: True면 Pi Camera 우선, False면 USB 우선
        """
        cameras_available = {
            'pi': CameraFactory.detect_pi_camera(),
            'usb': CameraFactory.detect_usb_camera()
        }
        
        print(f"📷 감지된 카메라: Pi={cameras_available['pi']}, USB={cameras_available['usb']}")
        
        if prefer_pi and cameras_available['pi']:
            print("🎥 Raspberry Pi Camera 사용")
            return PiCameraManager(), 'pi'
        elif cameras_available['usb']:
            print("📸 USB/OpenCV Camera 사용")
            return CameraManager(), 'usb'
        elif cameras_available['pi']:
            print("🎥 Raspberry Pi Camera 사용 (fallback)")
            return PiCameraManager(), 'pi'
        else:
            print("⚠️ 카메라 없음 - 더미 모드")
            return None, None
    
    @staticmethod
    def switch_camera(current_type):
        """
        다른 종류의 카메라로 전환
        """
        if current_type == 'pi':
            if CameraFactory.detect_usb_camera():
                print("📸 USB Camera로 전환")
                return CameraManager(), 'usb'
        elif current_type == 'usb':
            if CameraFactory.detect_pi_camera():
                print("🎥 Pi Camera로 전환")
                return PiCameraManager(), 'pi'
        
        print("⚠️ 다른 카메라 없음")
        return None, None