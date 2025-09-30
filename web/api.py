"""
FastAPI 라우터 모듈
웹 인터페이스와 API 엔드포인트 관리
"""

import asyncio
import subprocess
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, HTMLResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
import logging

# uvicorn 서버
import os
import signal
import threading
import time

logger = logging.getLogger(__name__)

class CCTVWebAPI:
    """CCTV 웹 API 관리 클래스"""
    
    def __init__(self, camera_manager):
        """
        Args:
            camera_manager: 카메라 관리 객체 (핵심 로직)
        """
        self.app = FastAPI()
        self.camera_manager = camera_manager
        self.recording_processes = {}  # 녹화 프로세스 추적

        # 정적 파일 서빙 설정
        self.app.mount("/static", StaticFiles(directory="web/static"), name="static")

        # 라우트 설정
        self.setup_routes()
    
    def setup_routes(self):
        """라우트 설정"""
        
        @self.app.get("/")
        async def index():
            """메인 페이지"""
            return FileResponse("web/static/index.html")
        
        @self.app.post("/switch/{camera_id}")
        async def switch_camera(camera_id: int):
            """카메라 전환 (싱글 뷰로 전환)"""
            if camera_id not in [0, 1]:
                raise HTTPException(status_code=400, detail="Invalid camera ID")
            
            # 듀얼 모드 비활성화
            if self.camera_manager.dual_mode:
                self.camera_manager.disable_dual_mode()
            
            success = await self.camera_manager.switch_camera(camera_id)
            
            if success:
                return {"success": True, "message": f"Switched to camera {camera_id}", "dual_mode": False}
            else:
                raise HTTPException(status_code=500, detail="Failed to switch camera")
        
        @self.app.post("/api/dual_mode/{enable}")
        async def toggle_dual_mode(enable: bool):
            """듀얼 모드 토글"""
            if enable:
                success = self.camera_manager.enable_dual_mode()
                if success:
                    return {"success": True, "message": "Dual mode enabled", "dual_mode": True}
                else:
                    raise HTTPException(status_code=500, detail="Failed to enable dual mode")
            else:
                self.camera_manager.disable_dual_mode()
                return {"success": True, "message": "Dual mode disabled", "dual_mode": False}
        
        @self.app.api_route("/stream", methods=["GET", "HEAD"])
        async def video_stream(request: Request):
            """비디오 스트림 (현재 선택된 카메라)"""
            client_ip = request.client.host
            
            # HEAD 요청 처리 (하트비트 체크용)
            if request.method == "HEAD":
                if self.camera_manager.is_camera_active():
                    return Response(
                        status_code=200, 
                        headers={"Content-Type": "multipart/x-mixed-replace; boundary=frame"}
                    )
                else:
                    return Response(status_code=503, headers={"Content-Type": "text/plain"})
            
            # 클라이언트 제한 확인
            if not self.camera_manager.can_accept_client(client_ip):
                max_clients = self.camera_manager.get_max_clients()
                raise HTTPException(
                    status_code=423,
                    detail=f"Maximum {max_clients} client(s) allowed. Server at capacity."
                )
            
            # 스트림 시작
            if not self.camera_manager.ensure_camera_started():
                raise HTTPException(status_code=500, detail="Failed to start camera")
            
            return StreamingResponse(
                self.camera_manager.generate_stream(client_ip),
                media_type="multipart/x-mixed-replace; boundary=frame"
            )
        
        @self.app.api_route("/stream/{camera_id}", methods=["GET", "HEAD"])
        async def camera_stream(camera_id: int, request: Request):
            """특정 카메라 스트림 (듀얼 모드용)"""
            client_ip = request.client.host
            
            if camera_id not in [0, 1]:
                raise HTTPException(status_code=400, detail="Invalid camera ID")
            
            # HEAD 요청 처리
            if request.method == "HEAD":
                if camera_id in self.camera_manager.camera_instances:
                    return Response(
                        status_code=200,
                        headers={"Content-Type": "multipart/x-mixed-replace; boundary=frame"}
                    )
                else:
                    return Response(status_code=503, headers={"Content-Type": "text/plain"})
            
            # 듀얼 모드가 아닌 경우 활성화
            if not self.camera_manager.dual_mode:
                if not self.camera_manager.enable_dual_mode():
                    raise HTTPException(status_code=500, detail="Failed to enable dual mode")
            
            # 카메라가 활성화되어 있는지 확인
            if camera_id not in self.camera_manager.camera_instances:
                raise HTTPException(status_code=503, detail=f"Camera {camera_id} not active")
            
            return StreamingResponse(
                self.camera_manager.generate_stream(client_ip, camera_id),
                media_type="multipart/x-mixed-replace; boundary=frame"
            )
        
        @self.app.get("/api/stats")
        async def get_stream_stats():
            """스트리밍 통계 조회"""
            return self.camera_manager.get_stats()
        
        @self.app.post("/api/resolution/{resolution}")
        async def change_resolution(resolution: str):
            """해상도 변경"""
            success = await self.camera_manager.change_resolution(resolution)
            
            if success:
                return {"success": True, "message": f"Resolution changed to {resolution}"}
            else:
                raise HTTPException(status_code=500, detail="Failed to change resolution")
        
        @self.app.get("/exit")
        async def exit_system():
            """시스템 종료 페이지"""
            return FileResponse("web/static/exit.html")

        # AI 감지 관련 엔드포인트
        @self.app.get("/api/ai/stats")
        async def get_ai_stats():
            """AI 감지 통계 조회"""
            try:
                stats = self.camera_manager.get_ai_stats()
                return {"success": True, "stats": stats}
            except Exception as e:
                logger.error(f"AI 통계 조회 오류: {e}")
                return {"success": False, "error": str(e)}

        @self.app.post("/api/ai/toggle/{enable}")
        async def toggle_ai_detection(enable: bool):
            """AI 감지 활성화/비활성화"""
            try:
                result = self.camera_manager.toggle_ai_detection(enable)
                status = "활성화" if enable else "비활성화"
                message = f"AI 감지가 {status}되었습니다"
                return {"success": result, "message": message, "enabled": result}
            except Exception as e:
                logger.error(f"AI 감지 토글 오류: {e}")
                return {"success": False, "error": str(e)}

        @self.app.get("/api/ai/detections")
        async def get_latest_detections():
            """최신 감지 결과 조회"""
            try:
                detections = {}
                for camera_id in [0, 1]:
                    camera_detections = self.camera_manager.latest_detections.get(camera_id, [])
                    detections[f"camera_{camera_id}"] = [
                        {
                            "label": det.label,
                            "confidence": det.confidence,
                            "bbox": det.bbox,
                            "class_id": det.class_id
                        }
                        for det in camera_detections
                    ]
                return {"success": True, "detections": detections}
            except Exception as e:
                logger.error(f"감지 결과 조회 오류: {e}")
                return {"success": False, "error": str(e)}

        @self.app.get("/api/notifications/events")
        async def get_recent_events():
            """최근 알림 이벤트 조회"""
            try:
                events = self.camera_manager.notification_system.get_recent_events(20)
                return {"success": True, "events": events}
            except Exception as e:
                logger.error(f"이벤트 조회 오류: {e}")
                return {"success": False, "error": str(e)}

        @self.app.post("/api/notifications/clear_cooldowns")
        async def clear_notification_cooldowns():
            """알림 쿨다운 초기화"""
            try:
                self.camera_manager.notification_system.clear_cooldowns()
                return {"success": True, "message": "알림 쿨다운이 초기화되었습니다"}
            except Exception as e:
                logger.error(f"쿨다운 초기화 오류: {e}")
                return {"success": False, "error": str(e)}

        @self.app.post("/api/notifications/toggle/{enable}")
        async def toggle_notifications(enable: bool):
            """알림 시스템 활성화/비활성화"""
            try:
                self.camera_manager.notification_system.set_enabled(enable)
                status = "활성화" if enable else "비활성화"
                return {"success": True, "message": f"알림 시스템이 {status}되었습니다", "enabled": enable}
            except Exception as e:
                logger.error(f"알림 토글 오류: {e}")
                return {"success": False, "error": str(e)}

        @self.app.post("/api/shutdown")
        async def shutdown_system():
            """시스템 안전 종료"""
            logger.info("[SHUTDOWN] System shutdown requested via web interface")
            
            # 카메라 관리자를 통해 종료
            await self.camera_manager.shutdown()
            #Uvicorn 서버 즉시 종료
            def force_shutdown():
                time.sleep(1)
                os._exit(0)  # 즉시 종료
            
            shutdown_thread = threading.Thread(target=force_shutdown)
            shutdown_thread.daemon = True
            shutdown_thread.start()
            
            return {"success": True, "message": "System shutting down"}

    # Continuous 30-second recording is handled by GPURecorder in webmain.py
    # Web interface focuses only on streaming functionality