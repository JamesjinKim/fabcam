from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from datetime import datetime
from typing import List
from contextlib import asynccontextmanager

from camera_manager import CameraManager
from models import FileInfo, RecordingStatus, ApiResponse

# 카메라 매니저 인스턴스 (2대 카메라 완전 분리)
camera_manager = CameraManager()

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    print("Starting Fabcam CCTV System...")
    try:
        
        # 모든 카메라 병렬 초기화
        try:
            camera_initialized = await camera_manager.initialize_all_cameras(timeout=30.0)
            
            if camera_initialized:
                print("✅ 카메라 시스템 초기화 완료 - 스트리밍 준비됨")
            else:
                print("❌ Warning: 카메라 초기화 실패 - 비디오 스트림 사용 불가")
                
        except Exception as e:
            print(f"Warning: 카메라 초기화 오류: {e}")
        
        yield
        
    finally:
        # Shutdown
        print("Shutting down Fabcam CCTV System...")
        try:
            camera_manager.cleanup_all()
            print("All camera resources cleaned up successfully")
        except Exception as e:
            print(f"Warning: Error during shutdown: {e}")
        finally:
            print("Shutdown complete")

app = FastAPI(
    title="Fabcam CCTV System", 
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙
app.mount("/static", StaticFiles(directory="../static"), name="static")
app.mount("/frontend", StaticFiles(directory="../frontend"), name="frontend")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    try:
        with open("../frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Frontend not found</h1>")

@app.get("/video_feed/{camera_id}")
async def video_feed(camera_id: int):
    camera = camera_manager.get_camera(camera_id)
    
    if not camera or not camera.is_streaming:
        raise HTTPException(status_code=503, detail=f"Camera {camera_id} not available")
    
    try:
        return StreamingResponse(
            camera.generate_frames(),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )
    except Exception as e:
        print(f"Camera {camera_id} video feed error: {e}")
        raise HTTPException(status_code=503, detail="Video stream interrupted")

@app.get("/video_feed")
async def video_feed_legacy():
    # 기존 호환성을 위한 레거시 엔드포인트 (카메라 1로 연결)
    return await video_feed(1)

@app.get("/video_feed_hd/{camera_id}")
async def video_feed_hd(camera_id: int):
    """HD 비디오 피드 (1280x720@25fps) - 전체화면용"""
    print(f"🎥 HD 비디오 피드 요청: 카메라 {camera_id}")
    
    camera = camera_manager.get_camera(camera_id)
    
    if not camera or not camera.is_streaming:
        raise HTTPException(status_code=503, detail=f"Camera {camera_id} not available")
    
    try:
        # HD 모드로 전환
        if not camera.switch_to_hd_mode():
            raise HTTPException(status_code=503, detail="Failed to switch to HD mode")
        
        print(f"🎬 HD 스트림 시작: 카메라 {camera_id} (1280x720@25fps)")
        return StreamingResponse(
            camera.generate_frames(),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )
    except Exception as e:
        print(f"HD Video feed error: {e}")
        # HD 모드 실패시 일반 모드로 복구
        try:
            camera.switch_to_normal_mode()
        except:
            pass
        raise HTTPException(status_code=503, detail="HD Video stream interrupted")

@app.post("/api/camera/{camera_id}/normal_mode")
async def switch_to_normal_mode(camera_id: int):
    """카메라를 일반 모드로 전환 (640x480@25fps)"""
    print(f"📺 일반 모드 전환 요청: 카메라 {camera_id}")
    
    camera = camera_manager.get_camera(camera_id)
    
    if not camera:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    
    try:
        if camera.switch_to_normal_mode():
            return ApiResponse(success=True, message=f"Camera {camera_id} switched to normal mode")
        else:
            raise HTTPException(status_code=500, detail="Failed to switch to normal mode")
    except Exception as e:
        print(f"Normal mode switch error: {e}")
        raise HTTPException(status_code=500, detail="Normal mode switch failed")

@app.post("/api/recording/start/{camera_id}")
async def start_recording(camera_id: int):
    camera = camera_manager.get_camera(camera_id)
    
    if not camera:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    
    filename = camera.start_recording()
    if filename:
        return ApiResponse(
            success=True,
            message=f"Camera {camera_id} recording started",
            data={"filename": filename, "camera_id": camera_id}
        )
    else:
        raise HTTPException(status_code=400, detail=f"Failed to start recording on camera {camera_id}")

@app.post("/api/recording/stop/{camera_id}")
async def stop_recording(camera_id: int):
    camera = camera_manager.get_camera(camera_id)
    
    if not camera:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    
    if camera.stop_recording():
        return ApiResponse(success=True, message=f"Camera {camera_id} recording stopped")
    else:
        raise HTTPException(status_code=400, detail=f"No active recording on camera {camera_id}")

@app.get("/api/recording/status/{camera_id}", response_model=RecordingStatus)
async def get_recording_status(camera_id: int):
    camera = camera_manager.get_camera(camera_id)
    
    if not camera:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    
    return RecordingStatus(is_recording=camera.get_recording_status())

@app.post("/api/snapshot/{camera_id}")
async def capture_snapshot(camera_id: int):
    camera = camera_manager.get_camera(camera_id)
    
    if not camera:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    
    filename = camera.capture_image()
    if filename:
        return ApiResponse(
            success=True,
            message=f"Camera {camera_id} snapshot captured",
            data={"filename": filename, "camera_id": camera_id}
        )
    else:
        raise HTTPException(status_code=400, detail=f"Failed to capture snapshot from camera {camera_id}")

# 레거시 엔드포인트들 (기존 호환성 유지)
@app.post("/api/recording/start")
async def start_recording_legacy():
    return await start_recording(1)

@app.post("/api/recording/stop")
async def stop_recording_legacy():
    return await stop_recording(1)

@app.get("/api/recording/status", response_model=RecordingStatus)
async def get_recording_status_legacy():
    return await get_recording_status(1)

@app.post("/api/snapshot")
async def capture_snapshot_legacy():
    return await capture_snapshot(1)

@app.get("/api/files/{camera_id}", response_model=List[FileInfo])
async def get_files(camera_id: int):
    files = []
    
    # 비디오 파일
    video_dir = f"../static/videos/camera{camera_id}"
    if os.path.exists(video_dir):
        for filename in os.listdir(video_dir):
            filepath = os.path.join(video_dir, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append(FileInfo(
                    filename=filename,
                    size=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    file_type="video"
                ))
    
    # 이미지 파일
    image_dir = f"../static/images/camera{camera_id}"
    if os.path.exists(image_dir):
        for filename in os.listdir(image_dir):
            filepath = os.path.join(image_dir, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append(FileInfo(
                    filename=filename,
                    size=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    file_type="image"
                ))
    
    return sorted(files, key=lambda x: x.created_at, reverse=True)

@app.get("/api/files", response_model=List[FileInfo])
async def get_files_legacy():
    # 레거시 지원: 모든 카메라의 파일을 통합해서 반환
    files = []
    
    for camera_id in [1, 2]:
        try:
            camera_files = await get_files(camera_id)
            files.extend(camera_files)
        except:
            continue
    
    return sorted(files, key=lambda x: x.created_at, reverse=True)

@app.get("/api/files/{camera_id}/{file_type}/{filename}")
async def download_file(camera_id: int, file_type: str, filename: str):
    if file_type not in ["videos", "images"]:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    filepath = os.path.join("..", "static", file_type, f"camera{camera_id}", filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(filepath, filename=filename)

@app.delete("/api/files/{camera_id}/{file_type}/{filename}")
async def delete_file(camera_id: int, file_type: str, filename: str):
    if file_type not in ["videos", "images"]:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    filepath = os.path.join("..", "static", file_type, f"camera{camera_id}", filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        os.remove(filepath)
        return ApiResponse(success=True, message="File deleted successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

# 레거시 파일 다운로드/삭제 엔드포인트 (카메라1 파일 우선 검색)
@app.get("/api/files/{file_type}/{filename}")
async def download_file_legacy(file_type: str, filename: str):
    # 카메라1 파일 먼저 찾기
    try:
        return await download_file(1, file_type, filename)
    except HTTPException:
        # 카메라2 파일 찾기
        try:
            return await download_file(2, file_type, filename)
        except HTTPException:
            raise HTTPException(status_code=404, detail="File not found")

@app.delete("/api/files/{file_type}/{filename}")
async def delete_file_legacy(file_type: str, filename: str):
    # 카메라1 파일 먼저 찾기
    try:
        return await delete_file(1, file_type, filename)
    except HTTPException:
        # 카메라2 파일 찾기
        try:
            return await delete_file(2, file_type, filename)
        except HTTPException:
            raise HTTPException(status_code=404, detail="File not found")

if __name__ == "__main__":
    import signal
    import sys
    
    def signal_handler(_sig, _frame):
        """Graceful shutdown on SIGINT/SIGTERM"""
        print("\nReceived shutdown signal...")
        sys.exit(0)
    
    # Signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,  # Disable reload to reduce complexity
            log_level="info",
            access_log=False,  # Reduce logging noise
            server_header=False,
            date_header=False
        )
    except KeyboardInterrupt:
        print("Keyboard interrupt received, shutting down gracefully...")
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        print("Server shutdown complete.")