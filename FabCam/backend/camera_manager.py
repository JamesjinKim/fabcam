import asyncio
import concurrent.futures
from camera1 import Camera1
from camera2 import Camera2

class CameraManager:
    def __init__(self):
        self.camera1 = Camera1()
        self.camera2 = Camera2()
        self.cameras = {
            1: self.camera1,
            2: self.camera2
        }
        print("🎬 CameraManager 초기화 완료 - 2대 카메라 등록")
    
    def get_camera(self, camera_id: int):
        """카메라 ID로 카메라 인스턴스 반환"""
        camera = self.cameras.get(camera_id)
        if camera is None:
            print(f"❌ 유효하지 않은 카메라 ID: {camera_id}")
        return camera
    
    def get_available_cameras(self):
        """사용 가능한 카메라 목록 반환"""
        return list(self.cameras.keys())
    
    def get_all_cameras_info(self):
        """모든 카메라 정보 반환"""
        info = {}
        for camera_id, camera in self.cameras.items():
            info[camera_id] = camera.get_camera_info()
        return info
    
    async def initialize_all_cameras(self, timeout=30.0):
        """모든 카메라를 병렬로 초기화"""
        print("🚀 모든 카메라 병렬 초기화 시작...")
        
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            try:
                # 모든 카메라 초기화를 병렬로 실행
                futures = {}
                for camera_id, camera in self.cameras.items():
                    future = executor.submit(camera.start_streaming)
                    futures[camera_id] = future
                
                # 각 카메라별로 타임아웃과 함께 대기
                for camera_id, future in futures.items():
                    try:
                        result = await asyncio.wait_for(
                            asyncio.wrap_future(future), 
                            timeout=timeout
                        )
                        results[camera_id] = result
                        
                        if result:
                            print(f"✅ 카메라{camera_id} 초기화 성공")
                        else:
                            print(f"❌ 카메라{camera_id} 초기화 실패")
                            
                    except asyncio.TimeoutError:
                        print(f"⏰ 카메라{camera_id} 초기화 타임아웃 ({timeout}초)")
                        results[camera_id] = False
                    except Exception as e:
                        print(f"❌ 카메라{camera_id} 초기화 오류: {e}")
                        results[camera_id] = False
                        
            except Exception as e:
                print(f"❌ 카메라 초기화 전체 오류: {e}")
                return False
        
        # 결과 요약
        success_count = sum(1 for result in results.values() if result)
        total_count = len(results)
        
        print(f"📊 카메라 초기화 완료: {success_count}/{total_count} 성공")
        
        if success_count > 0:
            print("✅ 최소 1대 이상의 카메라가 사용 가능합니다")
            return True
        else:
            print("❌ 사용 가능한 카메라가 없습니다")
            return False
    
    def start_streaming_all(self):
        """모든 카메라 스트리밍 시작"""
        results = {}
        for camera_id, camera in self.cameras.items():
            try:
                result = camera.start_streaming()
                results[camera_id] = result
                print(f"카메라{camera_id} 스트리밍 시작: {result}")
            except Exception as e:
                print(f"카메라{camera_id} 스트리밍 시작 오류: {e}")
                results[camera_id] = False
        return results
    
    def stop_streaming_all(self):
        """모든 카메라 스트리밍 중지"""
        for camera_id, camera in self.cameras.items():
            try:
                camera.stop_streaming()
                print(f"카메라{camera_id} 스트리밍 중지 완료")
            except Exception as e:
                print(f"카메라{camera_id} 스트리밍 중지 오류: {e}")
    
    def stop_recording_all(self):
        """모든 카메라 녹화 중지"""
        for camera_id, camera in self.cameras.items():
            try:
                if camera.is_recording:
                    camera.stop_recording()
                    print(f"카메라{camera_id} 녹화 중지 완료")
            except Exception as e:
                print(f"카메라{camera_id} 녹화 중지 오류: {e}")
    
    def get_streaming_status(self):
        """모든 카메라 스트리밍 상태 반환"""
        status = {}
        for camera_id, camera in self.cameras.items():
            status[camera_id] = {
                "is_streaming": camera.is_streaming,
                "is_recording": camera.is_recording,
                "is_hd_mode": camera.is_hd_mode
            }
        return status
    
    def cleanup_all(self):
        """모든 카메라 리소스 정리"""
        print("🧹 모든 카메라 리소스 정리 시작...")
        
        # 먼저 모든 녹화 중지
        self.stop_recording_all()
        
        # 모든 스트리밍 중지
        self.stop_streaming_all()
        
        print("✅ 모든 카메라 리소스 정리 완료")