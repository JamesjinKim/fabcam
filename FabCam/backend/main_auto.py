from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from datetime import datetime
from typing import List

from camera_factory import CameraFactory
from models import FileInfo, RecordingStatus, ApiResponse

app = FastAPI(title="Fabcam CCTV System", version="1.0.0")

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

# 카메라 매니저 초기화
camera, camera_type = CameraFactory.create_camera(prefer_pi=True)

@app.on_event("startup")
async def startup_event():
    print("Starting Fabcam CCTV System...")
    if camera and camera_type == 'usb':
        camera.start_streaming()
        print("Camera initialized successfully (OpenCV)")
    elif camera and camera_type == 'pi':
        print("Camera ready (Raspberry Pi)")
    else:
        print("Warning: No camera detected")

@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down Fabcam CCTV System...")
    if camera:
        if hasattr(camera, 'stop_stream'):
            camera.stop_stream()
        if hasattr(camera, 'stop_streaming'):
            camera.stop_streaming()
        if hasattr(camera, 'stop_recording'):
            camera.stop_recording()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    try:
        with open("../frontend/index.html", "r", encoding="utf-8") as f:
            content = f.read()
            
            # Pi Camera 사용시 비디오 소스 수정
            if camera_type == 'pi':
                content = content.replace(
                    'src="/video_feed"',
                    'src="http://' + os.environ.get('HOSTNAME', 'localhost') + ':8081/stream"'
                )
            
            return HTMLResponse(content=content)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Frontend not found</h1>")

@app.get("/video_feed")
async def video_feed():
    if not camera:
        raise HTTPException(status_code=503, detail="No camera available")
    
    if camera_type == 'pi':
        # Pi Camera는 별도 포트에서 스트리밍
        if not camera.is_streaming:
            camera.start_mjpeg_stream(8081)
        host = os.environ.get('HOSTNAME', 'localhost')
        return RedirectResponse(url=f"http://{host}:8081/stream")
    else:
        if not camera.is_streaming:
            raise HTTPException(status_code=503, detail="Camera not available")
        
        return StreamingResponse(
            camera.generate_frames(),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )

@app.post("/api/camera/switch")
async def switch_camera():
    """카메라 전환 API"""
    global camera, camera_type
    
    # 현재 카메라 정리
    if camera:
        if hasattr(camera, 'stop_stream'):
            camera.stop_stream()
        if hasattr(camera, 'stop_streaming'):
            camera.stop_streaming()
    
    # 새 카메라로 전환
    new_camera, new_type = CameraFactory.switch_camera(camera_type)
    
    if new_camera:
        camera = new_camera
        camera_type = new_type
        
        if camera_type == 'usb':
            camera.start_streaming()
        
        return ApiResponse(
            success=True,
            message=f"Switched to {new_type} camera",
            data={"camera_type": new_type}
        )
    else:
        raise HTTPException(status_code=404, detail="No alternative camera found")

@app.post("/api/camera/refresh")
async def refresh_camera():
    """카메라 재감지 및 초기화"""
    global camera, camera_type
    
    # 현재 카메라 정리
    if camera:
        if hasattr(camera, 'stop_stream'):
            camera.stop_stream()
        if hasattr(camera, 'stop_streaming'):
            camera.stop_streaming()
    
    # 카메라 재감지
    camera, camera_type = CameraFactory.create_camera(prefer_pi=True)
    
    if camera:
        if camera_type == 'usb':
            camera.start_streaming()
        
        return ApiResponse(
            success=True,
            message=f"Camera refreshed: {camera_type}",
            data={"camera_type": camera_type}
        )
    else:
        raise HTTPException(status_code=404, detail="No camera detected")

@app.post("/api/recording/start")
async def start_recording():
    if not camera:
        raise HTTPException(status_code=503, detail="No camera available")
    
    filename = camera.start_recording()
    if filename:
        return ApiResponse(
            success=True,
            message="Recording started",
            data={"filename": filename}
        )
    else:
        raise HTTPException(status_code=400, detail="Failed to start recording")

@app.post("/api/recording/stop")
async def stop_recording():
    if not camera:
        raise HTTPException(status_code=503, detail="No camera available")
    
    if camera.stop_recording():
        return ApiResponse(success=True, message="Recording stopped")
    else:
        raise HTTPException(status_code=400, detail="No active recording")

@app.get("/api/recording/status", response_model=RecordingStatus)
async def get_recording_status():
    if not camera:
        return RecordingStatus(is_recording=False)
    
    if hasattr(camera, 'is_recording'):
        return RecordingStatus(is_recording=camera.is_recording)
    else:
        return RecordingStatus(is_recording=camera.get_recording_status())

@app.post("/api/snapshot")
async def capture_snapshot():
    if not camera:
        raise HTTPException(status_code=503, detail="No camera available")
    
    filename = camera.capture_image()
    if filename:
        return ApiResponse(
            success=True,
            message="Snapshot captured",
            data={"filename": filename}
        )
    else:
        raise HTTPException(status_code=400, detail="Failed to capture snapshot")

@app.get("/api/files", response_model=List[FileInfo])
async def get_files():
    files = []
    
    # 비디오 파일
    video_dir = "../static/videos"
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
    image_dir = "../static/images"
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

@app.get("/api/files/{file_type}/{filename}")
async def download_file(file_type: str, filename: str):
    if file_type not in ["videos", "images"]:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    filepath = os.path.join("..", "static", file_type, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(filepath, filename=filename)

@app.delete("/api/files/{file_type}/{filename}")
async def delete_file(file_type: str, filename: str):
    if file_type not in ["videos", "images"]:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    filepath = os.path.join("..", "static", file_type, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        os.remove(filepath)
        return ApiResponse(success=True, message="File deleted successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

@app.get("/api/camera/info")
async def get_camera_info():
    """카메라 정보 반환"""
    return {
        "type": {
            'pi': "Raspberry Pi Camera",
            'usb': "USB/OpenCV Camera",
            None: "No Camera"
        }.get(camera_type, "Unknown"),
        "active": camera is not None,
        "camera_type": camera_type,
        "streaming": camera.is_streaming if camera and hasattr(camera, 'is_streaming') else False,
        "recording": camera.is_recording if camera and hasattr(camera, 'is_recording') else (
            camera.get_recording_status() if camera and hasattr(camera, 'get_recording_status') else False
        ),
        "stream_url": "http://localhost:8081/stream" if camera_type == 'pi' else "/video_feed"
    }

@app.get("/api/camera/detect")
async def detect_cameras():
    """사용 가능한 카메라 감지"""
    return {
        "pi_camera": CameraFactory.detect_pi_camera(),
        "usb_camera": CameraFactory.detect_usb_camera()
    }

if __name__ == "__main__":
    uvicorn.run(
        "main_auto:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )