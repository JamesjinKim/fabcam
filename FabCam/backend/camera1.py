from camera_base import CameraBase

class Camera1(CameraBase):
    def __init__(self):
        super().__init__(
            camera_index=0,
            camera_name="camera1",
            width=640,
            height=480
        )
        print(f"🎥 {self.camera_name} 인스턴스 생성 (Picamera2 인덱스: {self.camera_index})")
    
    def get_camera_info(self):
        """카메라1 고유 정보 반환"""
        return {
            "name": self.camera_name,
            "index": self.camera_index,
            "resolution": f"{self.width}x{self.height}",
            "hd_resolution": f"{self.hd_width}x{self.hd_height}",
            "is_streaming": self.is_streaming,
            "is_recording": self.is_recording,
            "is_hd_mode": self.is_hd_mode,
            "video_dir": self.video_dir,
            "image_dir": self.image_dir
        }