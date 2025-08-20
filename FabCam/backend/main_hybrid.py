from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from datetime import datetime
from typing import List
import json

from camera import CameraManager
from pi_camera import PiCameraManager
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

# 카메라 매니저 초기화 - Pi Camera 우선 시도
USE_PI_CAMERA = False
camera = None

try:
    pi_camera = PiCameraManager()
    if pi_camera.test_camera():
        print("🎥 Raspberry Pi Camera 사용")
        camera = pi_camera
        USE_PI_CAMERA = True
    else:
        print("📷 OpenCV 카메라 시도")
        camera = CameraManager()
        USE_PI_CAMERA = False
except Exception as e:
    print(f"📷 OpenCV 카메라 사용 (fallback): {e}")
    camera = CameraManager()
    USE_PI_CAMERA = False

@app.on_event("startup")
async def startup_event():
    print("Starting Fabcam CCTV System...")
    if USE_PI_CAMERA:
        print("Using Raspberry Pi Camera (rpicam)")
        # Pi Camera는 필요시에만 스트림 시작
    else:
        if camera.start_streaming():
            print("Camera initialized successfully (OpenCV)")
        else:
            print("Warning: Camera initialization failed")

@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down Fabcam CCTV System...")
    if USE_PI_CAMERA:
        camera.stop_stream()
        camera.stop_recording()
    else:
        camera.stop_recording()
        camera.stop_streaming()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    try:
        with open("../frontend/index.html", "r", encoding="utf-8") as f:
            content = f.read()
            
            # Pi Camera 사용시 비디오 소스 수정
            if USE_PI_CAMERA:
                content = content.replace(
                    'src="/video_feed"',
                    'src="http://' + os.environ.get('HOSTNAME', 'localhost') + ':8081/stream"'
                )
            
            return HTMLResponse(content=content)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Frontend not found</h1>")

@app.get("/video_feed")
async def video_feed():
    if USE_PI_CAMERA:
        # Pi Camera는 별도 포트에서 스트리밍
        if not camera.is_streaming:
            camera.start_mjpeg_stream(8081)
        # 클라이언트를 rpicam 스트림으로 리다이렉트
        host = os.environ.get('HOSTNAME', 'localhost')
        return RedirectResponse(url=f"http://{host}:8081/stream")
    else:
        if not camera.is_streaming:
            raise HTTPException(status_code=503, detail="Camera not available")
        
        return StreamingResponse(
            camera.generate_frames(),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )

@app.post("/api/recording/start")
async def start_recording():
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
    if camera.stop_recording():
        return ApiResponse(success=True, message="Recording stopped")
    else:
        raise HTTPException(status_code=400, detail="No active recording")

@app.get("/api/recording/status", response_model=RecordingStatus)
async def get_recording_status():
    if USE_PI_CAMERA:
        return RecordingStatus(is_recording=camera.is_recording)
    else:
        return RecordingStatus(is_recording=camera.get_recording_status())

@app.post("/api/snapshot")
async def capture_snapshot():
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
        "type": "Raspberry Pi Camera" if USE_PI_CAMERA else "OpenCV Camera",
        "streaming": camera.is_streaming if hasattr(camera, 'is_streaming') else False,
        "recording": camera.is_recording if hasattr(camera, 'is_recording') else camera.get_recording_status(),
        "stream_url": "http://localhost:8081/stream" if USE_PI_CAMERA else "/video_feed"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main_hybrid:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )