from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from datetime import datetime
from typing import List
import json

from camera import camera_manager
from models import FileInfo, RecordingStatus, ApiResponse

app = FastAPI(title="Fabcam CCTV System", version="2.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙
from pathlib import Path

# 현재 파일 기준으로 경로 설정
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
FRONTEND_DIR = BASE_DIR / "frontend"

# 디렉토리가 없으면 생성
STATIC_DIR.mkdir(exist_ok=True)
(STATIC_DIR / "videos").mkdir(exist_ok=True)
(STATIC_DIR / "images").mkdir(exist_ok=True)
(STATIC_DIR / "rec").mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

@app.on_event("startup")
async def startup_event():
    print("Starting Fabcam CCTV System (30 FPS)...")
    # 카메라 초기화 시도
    camera0_ok = camera_manager.init_camera(0)
    camera1_ok = camera_manager.init_camera(1)
    
    if camera0_ok or camera1_ok:
        print(f"Camera initialized: Camera0={camera0_ok}, Camera1={camera1_ok}")
        print("🚀 30 FPS 스트리밍 준비됨")
    else:
        print("Warning: No cameras initialized")

@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down Fabcam CCTV System...")
    camera_manager.cleanup()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    try:
        frontend_path = FRONTEND_DIR / "index.html"
        with open(frontend_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <h1>Fabcam CCTV System</h1>
        <p>Frontend not found</p>
        <p>30 FPS 스트리밍 시스템</p>
        """)

@app.get("/video_feed/{camera_id}")
async def video_feed(camera_id: int):
    """개별 카메라 MJPEG 스트림 (30 FPS)"""
    if camera_id not in [0, 1]:
        raise HTTPException(status_code=400, detail="Camera ID must be 0 or 1")
    
    # 카메라 사용 가능 확인
    status = camera_manager.get_camera_status()
    camera_key = f"camera{camera_id}"
    
    if not status[camera_key]["available"]:
        # 카메라 재초기화 시도
        print(f"카메라 {camera_id}번 재초기화 시도...")
        if camera_manager.init_camera(camera_id):
            print(f"카메라 {camera_id}번 재초기화 성공")
        else:
            raise HTTPException(status_code=503, detail=f"Camera {camera_id} not available")
    
    print(f"🚀 30 FPS 스트림 시작 - 카메라 {camera_id}")
    return StreamingResponse(
        camera_manager.generate_mjpeg_stream(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/api/camera/status")
async def camera_status():
    return camera_manager.get_camera_status()

@app.get("/api/system/status")
async def system_status():
    """시스템 리소스 상태 확인"""
    return camera_manager.get_system_status()

@app.get("/api/system/recommendation")
async def recording_recommendation():
    """녹화 권장사항 확인"""
    return camera_manager.check_recording_feasibility()

@app.post("/api/camera/{camera_id}/connect")
async def connect_camera(camera_id: int):
    """카메라 연결"""
    if camera_id not in [0, 1]:
        raise HTTPException(status_code=400, detail="Camera ID must be 0 or 1")
    
    if camera_manager.init_camera(camera_id):
        return ApiResponse(
            success=True,
            message=f"Camera {camera_id} connected (30 FPS)",
            data={"camera_id": camera_id, "fps": 30}
        )
    else:
        raise HTTPException(status_code=500, detail=f"Failed to connect camera {camera_id}")

@app.post("/api/camera/{camera_id}/disconnect")
async def disconnect_camera(camera_id: int):
    """카메라 연결 해제"""
    if camera_id not in [0, 1]:
        raise HTTPException(status_code=400, detail="Camera ID must be 0 or 1")
    
    camera_manager.stop_stream(camera_id)
    return ApiResponse(
        success=True,
        message=f"Camera {camera_id} disconnected",
        data={"camera_id": camera_id}
    )

@app.post("/api/camera/{camera_id}/start_continuous")
async def start_continuous_recording(camera_id: int):
    """개별 카메라 연속 녹화 시작"""
    if camera_id not in [0, 1]:
        raise HTTPException(status_code=400, detail="Camera ID must be 0 or 1")
    
    success = camera_manager.start_continuous_recording(camera_id)
    if success:
        return ApiResponse(
            success=True,
            message=f"Camera {camera_id} continuous recording started",
            data={"camera_id": camera_id}
        )
    else:
        raise HTTPException(status_code=500, detail=f"Failed to start continuous recording for camera {camera_id}")

@app.post("/api/camera/{camera_id}/stop_continuous")
async def stop_continuous_recording(camera_id: int):
    """개별 카메라 연속 녹화 중지"""
    if camera_id not in [0, 1]:
        raise HTTPException(status_code=400, detail="Camera ID must be 0 or 1")
    
    success = camera_manager.stop_continuous_recording(camera_id)
    if success:
        return ApiResponse(
            success=True,
            message=f"Camera {camera_id} continuous recording stopped",
            data={"camera_id": camera_id}
        )
    else:
        raise HTTPException(status_code=500, detail=f"Failed to stop continuous recording for camera {camera_id}")

@app.get("/api/camera/{camera_id}/continuous_status")
async def get_continuous_recording_status(camera_id: int):
    """개별 카메라 연속 녹화 상태"""
    if camera_id not in [0, 1]:
        raise HTTPException(status_code=400, detail="Camera ID must be 0 or 1")
    
    status = camera_manager.get_continuous_recording_status(camera_id)
    return status

@app.post("/api/recording/start")
async def start_recording(request: dict = {}):
    """수동 녹화 시작 (리소스 체크 포함)"""
    try:
        camera_ids = request.get("camera_ids") if request else None
        print(f"🎯 수동 녹화 API 요청: camera_ids={camera_ids}")
        success = camera_manager.start_manual_recording(camera_ids)
        if success:
            return ApiResponse(
                success=True,
                message="수동 녹화가 시작되었습니다",
                data={}
            )
        else:
            return ApiResponse(
                success=False,
                message="수동 녹화 시작 실패",
                data={}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"수동 녹화 오류: {str(e)}")

@app.post("/api/recording/stop")
async def stop_recording():
    """수동 녹화 중지"""
    try:
        saved_files = camera_manager.stop_manual_recording()
        return ApiResponse(
            success=True,
            message="수동 녹화가 중지되었습니다",
            data={"saved_files": saved_files, "file_count": len(saved_files)}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"수동 녹화 중지 오류: {str(e)}")

@app.get("/api/recording/status")
async def get_recording_status():
    """수동 녹화 상태 확인"""
    status = camera_manager.get_manual_recording_status()
    return RecordingStatus(
        is_recording=status.get("is_recording", False),
        start_time=status.get("start_time"),
        duration=status.get("duration")
    )

@app.post("/api/snapshot/{camera_id}")
async def capture_snapshot(camera_id: int, resolution: str = "hd"):
    """개별 카메라 스냅샷 캡처 (해상도 선택 가능)"""
    if camera_id not in [0, 1]:
        raise HTTPException(status_code=400, detail="Camera ID must be 0 or 1")
    
    # 해상도 검증
    valid_resolutions = ["vga", "hd", "fhd"]
    if resolution not in valid_resolutions:
        raise HTTPException(status_code=400, detail=f"Invalid resolution. Must be one of: {valid_resolutions}")
    
    filename = camera_manager.capture_snapshot(camera_id, resolution)
    if filename:
        resolution_names = {
            "vga": "640×480",
            "hd": "1280×720", 
            "fhd": "1920×1080"
        }
        return ApiResponse(
            success=True,
            message=f"Snapshot captured from camera {camera_id} at {resolution_names[resolution]}",
            data={"filename": filename, "camera_id": camera_id, "resolution": resolution}
        )
    else:
        raise HTTPException(status_code=400, detail=f"Failed to capture snapshot from camera {camera_id}")

@app.get("/api/files", response_model=List[FileInfo])
async def get_files():
    files = []
    
    # 비디오 파일
    video_dir = STATIC_DIR / "videos"
    if video_dir.exists():
        for filename in os.listdir(video_dir):
            filepath = video_dir / filename
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append(FileInfo(
                    filename=filename,
                    size=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    file_type="video"
                ))
    
    # 이미지 파일 (해상도별 폴더 포함)
    image_dir = STATIC_DIR / "images"
    if image_dir.exists():
        # 최상위 이미지 파일
        for filename in os.listdir(image_dir):
            filepath = image_dir / filename
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append(FileInfo(
                    filename=filename,
                    size=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    file_type="image"
                ))
        
        # 해상도별 폴더의 이미지 파일
        for res_folder in ["640x480", "1280x720", "1920x1080"]:
            res_dir = image_dir / res_folder
            if res_dir.exists() and res_dir.is_dir():
                for filename in os.listdir(res_dir):
                    filepath = res_dir / filename
                    if os.path.isfile(filepath):
                        stat = os.stat(filepath)
                        files.append(FileInfo(
                            filename=f"{res_folder}/{filename}",
                            size=stat.st_size,
                            created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            file_type="image"
                        ))
    
    return sorted(files, key=lambda x: x.created_at, reverse=True)

@app.get("/api/files/{file_type}/{path:path}")
async def download_file(file_type: str, path: str):
    if file_type not in ["videos", "images"]:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    # path는 파일명 또는 폴더/파일명 형태
    filepath = STATIC_DIR / file_type / path
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # 실제 파일명 추출 (경로에서 마지막 부분)
    actual_filename = Path(path).name
    
    return FileResponse(str(filepath), filename=actual_filename)

@app.delete("/api/files/{file_type}/{filename}")
async def delete_file(file_type: str, filename: str):
    if file_type not in ["videos", "images"]:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    filepath = STATIC_DIR / file_type / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        filepath.unlink()
        return ApiResponse(success=True, message="File deleted successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # 카메라 리소스 문제로 reload 비활성화
        log_level="info"
    )