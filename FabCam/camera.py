#!/usr/bin/env python3
"""
rpicam-vid 기반 30 FPS 듀얼 카메라 매니저 - 스트림 공유 아키텍처
"""

import subprocess
import threading
import time
import os
import signal
import queue
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Generator, Dict, Set, List
import tempfile
import psutil

class SharedStreamManager:
    """단일 프로세스에서 다중 클라이언트를 위한 스트림 공유 매니저"""
    
    def __init__(self, camera_num: int, camera_manager=None):
        self.camera_num = camera_num
        self.camera_manager = camera_manager
        self.process: Optional[subprocess.Popen] = None
        self.clients: Dict[str, queue.Queue] = {}  # client_id: frame_queue
        self.is_running = False
        self.frame_reader_thread: Optional[threading.Thread] = None
        self.latest_frame: Optional[bytes] = None
        self.frame_lock = threading.Lock()
        self.continuous_was_recording = False  # 연속 녹화 상태 저장
        
    def start_stream(self) -> bool:
        """스트림 시작 (연속 녹화 일시 중단)"""
        if self.is_running:
            return True
        
        # 스트림 시작 전 연속 녹화 중단
        if self.camera_manager and self.camera_num in self.camera_manager.continuous_recorders:
            recorder = self.camera_manager.continuous_recorders[self.camera_num]
            if recorder.is_recording:
                print(f"⏸️ 스트림을 위해 연속 녹화 일시 중단 (카메라 {self.camera_num})")
                recorder.stop_continuous_recording()
                self.continuous_was_recording = True
                time.sleep(0.5)  # 프로세스 종료 대기
            
        try:
            # FIFO 사용하여 stdout 문제 회피
            import tempfile
            self.fifo_path = f"/tmp/rpicam_fifo_{self.camera_num}"
            
            # 기존 FIFO 제거
            try:
                os.unlink(self.fifo_path)
            except FileNotFoundError:
                pass
            
            # FIFO 생성
            os.mkfifo(self.fifo_path)
            
            cmd = [
                "rpicam-vid",
                "--camera", str(self.camera_num),
                "--width", "640",
                "--height", "480",
                "--framerate", "30",
                "--codec", "mjpeg",
                "--output", self.fifo_path,
                "--timeout", "0",
                "--nopreview"
            ]
            
            print(f"🎬 공유 스트림 시작 (카메라 {self.camera_num}): {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            
            # FIFO에서 읽기 위한 파일 열기 (non-blocking)
            self.fifo_fd = os.open(self.fifo_path, os.O_RDONLY | os.O_NONBLOCK)
            
            self.is_running = True
            self.frame_reader_thread = threading.Thread(target=self._frame_reader, daemon=True)
            self.frame_reader_thread.start()
            
            return True
            
        except Exception as e:
            print(f"스트림 시작 오류 (카메라 {self.camera_num}): {e}")
            return False
    
    def stop_stream(self):
        """스트림 중지"""
        self.is_running = False
        
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except:
                self.process.kill()
        
        # FIFO 정리
        if hasattr(self, 'fifo_fd'):
            try:
                os.close(self.fifo_fd)
            except:
                pass
        
        if hasattr(self, 'fifo_path'):
            try:
                os.unlink(self.fifo_path)
            except:
                pass
        
        self.clients.clear()
        
        # 스트림 중지 후 연속 녹화 재시작
        if self.continuous_was_recording and self.camera_manager and self.camera_num in self.camera_manager.continuous_recorders:
            print(f"▶️ 스트림 종료, 연속 녹화 재시작 (카메라 {self.camera_num})")
            time.sleep(0.5)  # 스트림 프로세스 종료 대기
            self.camera_manager.continuous_recorders[self.camera_num].start_continuous_recording()
            self.continuous_was_recording = False
        
        print(f"🛑 공유 스트림 중지 (카메라 {self.camera_num})")
    
    def add_client(self) -> str:
        """클라이언트 추가 및 ID 반환"""
        client_id = str(uuid.uuid4())
        self.clients[client_id] = queue.Queue(maxsize=5)  # 최대 5프레임 버퍼
        print(f"👤 클라이언트 추가 (카메라 {self.camera_num}): {client_id[:8]}... (총 {len(self.clients)}명)")
        return client_id
    
    def remove_client(self, client_id: str):
        """클라이언트 제거"""
        if client_id in self.clients:
            del self.clients[client_id]
            print(f"👤 클라이언트 제거 (카메라 {self.camera_num}): {client_id[:8]}... (남은 {len(self.clients)}명)")
            
            # 클라이언트가 없으면 스트림 중지
            if not self.clients and self.is_running:
                self.stop_stream()
    
    def _frame_reader(self):
        """프레임 읽기 및 클라이언트 배포"""
        buffer = b""
        frame_start = b"\xff\xd8"
        frame_end = b"\xff\xd9"
        
        # stderr 출력 체크
        if self.process and self.process.stderr:
            try:
                import select
                import os
                # stderr를 non-blocking으로 설정
                fd = self.process.stderr.fileno()
                fl = os.fcntl(fd, os.fcntl.F_GETFL)
                os.fcntl(fd, os.fcntl.F_SETFL, fl | os.O_NONBLOCK)
            except:
                pass
        
        no_data_count = 0
        while self.is_running:
            if not self.process or self.process.poll() is not None:
                print(f"프로세스 종료됨 (카메라 {self.camera_num})")
                # stderr 출력 확인
                if self.process and self.process.stderr:
                    try:
                        stderr_output = self.process.stderr.read()
                        if stderr_output:
                            print(f"rpicam-vid stderr (카메라 {self.camera_num}): {stderr_output.decode()}")
                    except:
                        pass
                break
                
            try:
                # FIFO에서 데이터 읽기
                chunk = os.read(self.fifo_fd, 4096)
                if not chunk:
                    no_data_count += 1
                    if no_data_count % 1000 == 0:  # 10초마다 로그
                        print(f"데이터 없음 카운트 (카메라 {self.camera_num}): {no_data_count}")
                        # stderr 체크
                        if self.process and self.process.stderr:
                            try:
                                stderr_data = self.process.stderr.read()
                                if stderr_data:
                                    print(f"rpicam-vid stderr: {stderr_data.decode()}")
                            except:
                                pass
                    time.sleep(0.01)
                    continue
                
                no_data_count = 0  # 데이터를 받으면 카운트 리셋
                
            except BlockingIOError:
                # FIFO에 데이터가 없으면 잠시 대기
                time.sleep(0.01)
                continue
            except Exception as e:
                print(f"FIFO 읽기 오류 (카메라 {self.camera_num}): {e}")
                break
                
            buffer += chunk
            
            # 완전한 JPEG 프레임 찾기
            while True:
                start_idx = buffer.find(frame_start)
                if start_idx == -1:
                    break
                
                end_idx = buffer.find(frame_end, start_idx + 2)
                if end_idx == -1:
                    break
                
                # 완전한 프레임 추출
                frame_data = buffer[start_idx:end_idx + 2]
                buffer = buffer[end_idx + 2:]
                
                # MJPEG boundary format
                mjpeg_frame = (b'--frame\r\n'
                             b'Content-Type: image/jpeg\r\n'
                             b'Content-Length: ' + str(len(frame_data)).encode() + b'\r\n\r\n' +
                             frame_data + b'\r\n')
                
                # 최신 프레임 저장 (스냅샷용)
                with self.frame_lock:
                    self.latest_frame = frame_data
                
                # 모든 클라이언트에게 프레임 배포
                self._distribute_frame(mjpeg_frame)
    
    def _distribute_frame(self, frame: bytes):
        """모든 클라이언트에게 프레임 배포"""
        dead_clients = []
        
        for client_id, client_queue in self.clients.items():
            try:
                # 큐가 가득 차면 오래된 프레임 제거
                if client_queue.full():
                    try:
                        client_queue.get_nowait()
                    except queue.Empty:
                        pass
                
                client_queue.put(frame, block=False)
                
            except queue.Full:
                # 클라이언트가 응답하지 않으면 제거 대상으로 표시
                dead_clients.append(client_id)
            except Exception as e:
                print(f"프레임 배포 오류 (클라이언트 {client_id[:8]}...): {e}")
                dead_clients.append(client_id)
        
        # 응답하지 않는 클라이언트 제거
        for client_id in dead_clients:
            self.remove_client(client_id)
    
    def get_client_stream(self, client_id: str) -> Generator[bytes, None, None]:
        """특정 클라이언트를 위한 스트림 제너레이터"""
        if client_id not in self.clients:
            return
            
        client_queue = self.clients[client_id]
        
        try:
            while client_id in self.clients and self.is_running:
                try:
                    frame = client_queue.get(timeout=1.0)
                    yield frame
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"클라이언트 스트림 오류 ({client_id[:8]}...): {e}")
                    break
        finally:
            self.remove_client(client_id)


class ContinuousRecorder:
    """블랙박스 형태 연속 녹화 시스템 (640×480)"""
    
    def __init__(self, camera_num: int, output_dir: Path):
        self.camera_num = camera_num
        self.output_dir = output_dir
        self.process: Optional[subprocess.Popen] = None
        self.is_recording = False
        self.start_time: Optional[datetime] = None
        self.current_file_index = 0
        
        # 30초 세그먼트 (개발용)
        self.segment_duration = 30
        
        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def start_continuous_recording(self) -> bool:
        """연속 녹화 시작"""
        if self.is_recording:
            return True
            
        try:
            # 기존 파일 인덱스 확인
            self._update_file_index()
            
            # 출력 파일 설정 (단일 파일, 타임스탬프 기반)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"rec_{self.camera_num}_{timestamp}.mp4"
            
            cmd = [
                "rpicam-vid",
                "--camera", str(self.camera_num),
                "--width", "640",
                "--height", "480", 
                "--framerate", "30",
                "--codec", "h264",
                "--output", str(output_file),
                "--timeout", str(self.segment_duration * 1000),  # 30초 녹화 후 종료
                "--nopreview"
            ]
            
            print(f"🎬 연속 녹화 시작 (카메라 {self.camera_num}, 640×480): {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            
            self.is_recording = True
            self.start_time = datetime.now()
            
            # 자동 재시작 모니터링 시작
            self._start_monitoring()
            
            print(f"✅ 카메라 {self.camera_num} 연속 녹화 시작됨 ({self.segment_duration}초 세그먼트)")
            return True
            
        except Exception as e:
            print(f"❌ 연속 녹화 시작 오류 (카메라 {self.camera_num}): {e}")
            return False
    
    def stop_continuous_recording(self):
        """연속 녹화 중지"""
        if not self.is_recording:
            return
            
        self.is_recording = False
        
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
        
        duration = None
        if self.start_time:
            duration = datetime.now() - self.start_time
            
        print(f"🛑 카메라 {self.camera_num} 연속 녹화 중지됨 (총 시간: {duration})")
    
    def _start_monitoring(self):
        """연속 녹화 모니터링 시작"""
        def monitor_process():
            while self.is_recording:
                if self.process and self.process.poll() is not None:
                    # 프로세스가 종료됨 (30초 세그먼트 완료)
                    if self.is_recording:  # 여전히 녹화 중이어야 함
                        print(f"🔄 연속 녹화 세그먼트 완료, 재시작 (카메라 {self.camera_num})")
                        self._restart_recording()
                time.sleep(1)
        
        monitoring_thread = threading.Thread(target=monitor_process, daemon=True)
        monitoring_thread.start()
    
    def _restart_recording(self):
        """연속 녹화 재시작 (새 세그먼트)"""
        if not self.is_recording:
            return
        
        try:
            # 새 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"rec_{self.camera_num}_{timestamp}.mp4"
            
            cmd = [
                "rpicam-vid",
                "--camera", str(self.camera_num),
                "--width", "640",
                "--height", "480", 
                "--framerate", "30",
                "--codec", "h264",
                "--output", str(output_file),
                "--timeout", str(self.segment_duration * 1000),
                "--nopreview"
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            
            print(f"📹 연속 녹화 새 세그먼트 시작 (카메라 {self.camera_num})")
            
        except Exception as e:
            print(f"❌ 연속 녹화 재시작 오류 (카메라 {self.camera_num}): {e}")
            self.is_recording = False
    
    def _update_file_index(self):
        """기존 파일 개수 확인하여 인덱스 설정"""
        existing_files = list(self.output_dir.glob(f"rec_{self.camera_num}_*.mp4"))
        if existing_files:
            # 파일 번호 추출하여 다음 인덱스 설정
            numbers = []
            for file in existing_files:
                try:
                    # rec_0_0001.mp4 -> 1
                    num = int(file.stem.split('_')[-1])
                    numbers.append(num)
                except:
                    continue
            self.current_file_index = max(numbers) + 1 if numbers else 0
        else:
            self.current_file_index = 0
    
    def get_recording_status(self) -> dict:
        """녹화 상태 반환"""
        status = {
            "is_recording": self.is_recording,
            "camera_id": self.camera_num,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "duration": None,
            "current_segment": self.current_file_index
        }
        
        if self.is_recording and self.start_time:
            duration = datetime.now() - self.start_time
            status["duration"] = int(duration.total_seconds())
            
        return status
    
    def cleanup_old_files(self, max_files: int = 48):
        """오래된 파일 정리 (기본: 48개 = 24시간)"""
        try:
            files = sorted(
                self.output_dir.glob(f"rec_{self.camera_num}_*.mp4"),
                key=lambda f: f.stat().st_mtime
            )
            
            if len(files) > max_files:
                files_to_delete = files[:-max_files]
                for file in files_to_delete:
                    file.unlink()
                    print(f"🗑️ 오래된 녹화 파일 삭제: {file.name}")
                    
        except Exception as e:
            print(f"파일 정리 오류 (카메라 {self.camera_num}): {e}")


class ManualRecorder:
    """사용자 제어 기본 녹화 시스템 (640×480)"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.recording_processes: Dict[int, subprocess.Popen] = {}
        self.recording_start_time: Optional[datetime] = None
        self.recording_files: Dict[int, str] = {}  # camera_id: filename
        
        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def start_manual_recording(self, camera_ids: List[int]) -> bool:
        """수동 녹화 시작 (640×480)"""
        if self.recording_processes:
            print("⚠️ 이미 수동 녹화가 진행 중입니다")
            return False
            
        try:
            self.recording_start_time = datetime.now()
            timestamp = self.recording_start_time.strftime("%Y%m%d_%H%M%S")
            started_cameras = []
            
            for camera_id in camera_ids:
                print(f"📋 수동 녹화 시도: 카메라 {camera_id}")
                filename = f"manual_{timestamp}_cam{camera_id}.mp4"
                filepath = self.output_dir / filename
                
                cmd = [
                    "rpicam-vid",
                    "--camera", str(camera_id),
                    "--width", "640",
                    "--height", "480",
                    "--framerate", "30",
                    "--codec", "h264",
                    "--output", str(filepath),
                    "--timeout", "0",  # 무한 실행 (수동 중지까지)
                    "--nopreview"
                ]
                
                print(f"🎬 수동 녹화 시작 (카메라 {camera_id}, 640×480): {filename}")
                print(f"💾 저장 경로: {filepath}")
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=0
                )
                
                # 프로세스가 정상 시작되었는지 확인
                time.sleep(0.8)  # 조금 더 긴 대기
                if process.poll() is not None:
                    # 프로세스가 이미 종료됨
                    stderr_output = process.stderr.read().decode('utf-8', errors='ignore')
                    stdout_output = process.stdout.read().decode('utf-8', errors='ignore')
                    print(f"❌ 카메라 {camera_id} 녹화 프로세스 실패")
                    print(f"  stderr: {stderr_output}")
                    print(f"  stdout: {stdout_output}")
                    print(f"  return code: {process.returncode}")
                    continue
                
                self.recording_processes[camera_id] = process
                self.recording_files[camera_id] = filename
                started_cameras.append(camera_id)
            
            if started_cameras:
                print(f"✅ 수동 녹화 시작됨: 카메라 {started_cameras} (640×480)")
                return True
            else:
                print("❌ 수동 녹화를 시작할 수 있는 카메라가 없습니다")
                return False
                
        except Exception as e:
            print(f"❌ 수동 녹화 시작 오류: {e}")
            self.stop_manual_recording()  # 실패시 정리
            return False
    
    def stop_manual_recording(self) -> Dict[int, str]:
        """수동 녹화 중지 및 파일 반환"""
        if not self.recording_processes:
            return {}
            
        saved_files = {}
        duration = None
        
        if self.recording_start_time:
            duration = datetime.now() - self.recording_start_time
        
        try:
            for camera_id, process in list(self.recording_processes.items()):
                try:
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=5)
                    
                    filename = self.recording_files.get(camera_id)
                    if filename:
                        filepath = self.output_dir / filename
                        if filepath.exists() and filepath.stat().st_size > 0:
                            saved_files[camera_id] = filename
                            print(f"💾 수동 녹화 저장됨 (카메라 {camera_id}): {filename}")
                        else:
                            print(f"⚠️ 수동 녹화 파일이 생성되지 않음 (카메라 {camera_id})")
                    
                except Exception as e:
                    print(f"수동 녹화 중지 오류 (카메라 {camera_id}): {e}")
            
            print(f"🛑 수동 녹화 완료 (총 시간: {duration}, 저장된 파일: {len(saved_files)}개)")
            
        finally:
            # 정리
            self.recording_processes.clear()
            self.recording_files.clear()
            self.recording_start_time = None
            
        return saved_files
    
    def get_recording_status(self) -> dict:
        """수동 녹화 상태 반환"""
        status = {
            "is_recording": bool(self.recording_processes),
            "camera_count": len(self.recording_processes),
            "cameras": list(self.recording_processes.keys()),
            "start_time": self.recording_start_time.isoformat() if self.recording_start_time else None,
            "duration": None,
            "files": dict(self.recording_files)
        }
        
        if self.recording_start_time and self.recording_processes:
            duration = datetime.now() - self.recording_start_time
            status["duration"] = int(duration.total_seconds())
            
        return status
    
    def is_recording(self) -> bool:
        """녹화 중인지 확인"""
        return bool(self.recording_processes)


class ResourceMonitor:
    """시스템 리소스 모니터링 및 제어"""
    
    def __init__(self):
        self.cpu_threshold = 90  # CPU 사용률 임계값 (%)
        self.memory_threshold = 85  # 메모리 사용률 임계값 (%)
        self.monitoring = False
        
    def get_system_status(self) -> dict:
        """현재 시스템 리소스 상태 반환"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "cores": psutil.cpu_count(),
                    "status": "high" if cpu_percent > self.cpu_threshold else "normal"
                },
                "memory": {
                    "percent": memory.percent,
                    "used_gb": round(memory.used / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2),
                    "status": "high" if memory.percent > self.memory_threshold else "normal"
                },
                "disk": {
                    "percent": disk.percent,
                    "free_gb": round(disk.free / (1024**3), 2),
                    "total_gb": round(disk.total / (1024**3), 2)
                },
                "processes": {
                    "total": len(psutil.pids()),
                    "python": len([p for p in psutil.process_iter(['name']) if 'python' in p.info['name'].lower()])
                }
            }
        except Exception as e:
            print(f"리소스 모니터링 오류: {e}")
            return {"error": str(e)}
    
    def is_system_overloaded(self) -> bool:
        """시스템 과부하 상태 확인"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory_percent = psutil.virtual_memory().percent
            
            return cpu_percent > self.cpu_threshold or memory_percent > self.memory_threshold
        except:
            return False
    
    def get_recording_recommendation(self) -> dict:
        """리소스 상태 기반 녹화 권장사항"""
        status = self.get_system_status()
        cpu_percent = status.get("cpu", {}).get("percent", 0)
        memory_percent = status.get("memory", {}).get("percent", 0)
        
        if cpu_percent > 95 or memory_percent > 90:
            return {
                "recommendation": "critical",
                "message": "시스템 과부하! 연속 녹화 일시 정지 권장",
                "suggested_action": "pause_continuous"
            }
        elif cpu_percent > 85 or memory_percent > 80:
            return {
                "recommendation": "warning", 
                "message": "높은 시스템 부하, 해상도 다운그레이드 권장",
                "suggested_action": "reduce_quality"
            }
        else:
            return {
                "recommendation": "normal",
                "message": "시스템 정상, 모든 기능 사용 가능",
                "suggested_action": "none"
            }


class CameraManager:
    """스트림 공유 기반 카메라 매니저"""
    
    def __init__(self):
        self.camera0_available = False
        self.camera1_available = False
        self.is_recording = False
        
        # 공유 스트림 매니저
        self.shared_streams: Dict[int, SharedStreamManager] = {}
        
        # 연속 녹화 매니저 (블랙박스)
        self.continuous_recorders: Dict[int, ContinuousRecorder] = {}
        
        # 수동 녹화 매니저 (고품질)
        self.manual_recorder: Optional[ManualRecorder] = None
        
        # 리소스 모니터링
        self.resource_monitor = ResourceMonitor()
        
        # 저장 디렉토리
        self.base_dir = Path(__file__).parent
        self.snapshot_dir = self.base_dir / "static" / "images"
        self.video_dir = self.base_dir / "static" / "videos"
        self.rec_dir = self.base_dir / "static" / "rec"
        
        # 디렉토리 생성
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.video_dir.mkdir(parents=True, exist_ok=True)
        self.rec_dir.mkdir(parents=True, exist_ok=True)
        
        print("🚀 블랙박스 카메라 매니저 초기화 (스트림 + 연속녹화 + 수동녹화)")
        self._detect_cameras()
        
        # 카메라 감지 후 녹화 매니저 초기화
        self._init_continuous_recorders()
        self._init_manual_recorder()
    
    def _detect_cameras(self):
        """사용 가능한 카메라 감지"""
        try:
            result = subprocess.run(
                ["rpicam-hello", "--list-cameras"],
                capture_output=True,
                text=True,
                timeout=3
            )
            
            if result.returncode == 0 and "Available cameras" in result.stdout:
                # 카메라 개수 파악
                lines = result.stdout.split('\n')
                camera_count = 0
                for line in lines:
                    if line.strip().startswith(('0 :', '1 :')):
                        camera_count += 1
                
                self.camera0_available = camera_count >= 1
                self.camera1_available = camera_count >= 2
                
                print(f"📷 감지된 카메라: {camera_count}개")
                if self.camera0_available:
                    print("   - 카메라 0번: 사용 가능 (30 FPS)")
                if self.camera1_available:
                    print("   - 카메라 1번: 사용 가능 (30 FPS)")
            else:
                print("❌ 카메라를 감지할 수 없습니다")
                
        except Exception as e:
            print(f"❌ 카메라 감지 오류: {e}")
    
    def _init_continuous_recorders(self):
        """연속 녹화 매니저 초기화 및 자동 시작"""
        try:
            if self.camera0_available:
                rec_dir_0 = self.rec_dir / "camera0"
                self.continuous_recorders[0] = ContinuousRecorder(0, rec_dir_0)
                
            if self.camera1_available:
                rec_dir_1 = self.rec_dir / "camera1"
                self.continuous_recorders[1] = ContinuousRecorder(1, rec_dir_1)
            
            print(f"📹 연속 녹화 매니저 초기화 완료 ({len(self.continuous_recorders)}개 카메라)")
            print("📺 스트림 우선 모드: 연속 녹화는 수동으로 시작하세요")
            
        except Exception as e:
            print(f"❌ 연속 녹화 매니저 초기화 오류: {e}")
    
    def _start_blackbox_recording(self):
        """블랙박스 모드: 자동 연속 녹화 시작"""
        try:
            started_cameras = []
            for camera_id, recorder in self.continuous_recorders.items():
                if recorder.start_continuous_recording():
                    started_cameras.append(camera_id)
            
            if started_cameras:
                print(f"🚗 블랙박스 모드 활성화! 연속 녹화 시작: 카메라 {started_cameras}")
            else:
                print("⚠️ 연속 녹화를 시작할 수 있는 카메라가 없습니다")
                
        except Exception as e:
            print(f"❌ 블랙박스 모드 시작 오류: {e}")
    
    def _init_manual_recorder(self):
        """수동 녹화 매니저 초기화"""
        try:
            self.manual_recorder = ManualRecorder(self.video_dir)
            print("📹 수동 녹화 매니저 초기화 완료 (640×480)")
        except Exception as e:
            print(f"❌ 수동 녹화 매니저 초기화 오류: {e}")
    
    def start_manual_recording(self, camera_ids: List[int] = None) -> bool:
        """수동 녹화 시작 (640×480, 연속 녹화 일시 중단)"""
        if camera_ids is None:
            # 기본값: 사용 가능한 모든 카메라
            camera_ids = []
            if self.camera0_available:
                camera_ids.append(0)
            if self.camera1_available:
                camera_ids.append(1)
        
        if not self.manual_recorder:
            print("❌ 수동 녹화 매니저가 초기화되지 않았습니다")
            return False
        
        # 수동 녹화를 위해 연속 녹화 일시 중단
        print(f"📋 수동 녹화 요청 카메라: {camera_ids}")
        paused_continuous = []
        for camera_id in camera_ids:
            print(f"  - 카메라 {camera_id} 연속 녹화 상태 확인...")
            if camera_id in self.continuous_recorders:
                recorder = self.continuous_recorders[camera_id]
                print(f"    연속 녹화 중: {recorder.is_recording}")
                if recorder.is_recording:
                    print(f"⏸️ 연속 녹화 일시 중단 (카메라 {camera_id})")
                    recorder.stop_continuous_recording()
                    paused_continuous.append(camera_id)
                    # 중단 후 잠시 대기
                    time.sleep(1.0)
                    print(f"    연속 녹화 중단 완료 (카메라 {camera_id})")
            else:
                print(f"    연속 녹화 매니저 없음 (카메라 {camera_id})")
        
        # 수동 녹화 시작
        success = self.manual_recorder.start_manual_recording(camera_ids)
        
        # 수동 녹화 시작 실패 시 연속 녹화 재시작
        if not success:
            for camera_id in paused_continuous:
                if camera_id in self.continuous_recorders:
                    print(f"▶️ 연속 녹화 재시작 (카메라 {camera_id})")
                    self.continuous_recorders[camera_id].start_continuous_recording()
        
        return success
    
    def stop_manual_recording(self) -> Dict[int, str]:
        """수동 녹화 중지 및 연속 녹화 재시작"""
        if not self.manual_recorder:
            return {}
        
        # 수동 녹화에서 사용 중이던 카메라 목록 저장
        recording_cameras = list(self.manual_recorder.recording_processes.keys())
        
        # 수동 녹화 중지
        result = self.manual_recorder.stop_manual_recording()
        
        # 연속 녹화 재시작
        for camera_id in recording_cameras:
            if camera_id in self.continuous_recorders:
                print(f"▶️ 연속 녹화 재시작 (카메라 {camera_id})")
                self.continuous_recorders[camera_id].start_continuous_recording()
        
        return result
    
    def get_manual_recording_status(self) -> dict:
        """수동 녹화 상태 확인"""
        if not self.manual_recorder:
            return {"is_recording": False}
        return self.manual_recorder.get_recording_status()
    
    def get_system_status(self) -> dict:
        """시스템 리소스 상태 확인"""
        return self.resource_monitor.get_system_status()
    
    def check_recording_feasibility(self) -> dict:
        """녹화 가능성 및 권장사항 확인"""
        return self.resource_monitor.get_recording_recommendation()
    
    def start_continuous_recording(self, camera_id: int) -> bool:
        """개별 카메라 연속 녹화 시작"""
        if camera_id not in self.continuous_recorders:
            print(f"❌ 카메라 {camera_id} 연속 녹화 매니저가 없습니다")
            return False
        
        # 스트림이 실행 중이면 중지
        if camera_id in self.shared_streams:
            stream = self.shared_streams[camera_id]
            if stream.is_running:
                print(f"⏸️ 연속 녹화를 위해 스트림 중지 (카메라 {camera_id})")
                stream.stop_stream()
                time.sleep(0.5)
        
        return self.continuous_recorders[camera_id].start_continuous_recording()
    
    def stop_continuous_recording(self, camera_id: int) -> bool:
        """개별 카메라 연속 녹화 중지"""
        if camera_id not in self.continuous_recorders:
            print(f"❌ 카메라 {camera_id} 연속 녹화 매니저가 없습니다")
            return False
        
        self.continuous_recorders[camera_id].stop_continuous_recording()
        
        # 연속 녹화 중지 후 스트림 재시작
        if camera_id in self.shared_streams:
            print(f"▶️ 연속 녹화 중지, 스트림 재시작 (카메라 {camera_id})")
            time.sleep(0.5)
            self.shared_streams[camera_id].start_stream()
        
        return True
    
    def get_continuous_recording_status(self, camera_id: int) -> dict:
        """개별 카메라 연속 녹화 상태"""
        if camera_id not in self.continuous_recorders:
            return {"is_recording": False, "error": "Camera not found"}
        
        return self.continuous_recorders[camera_id].get_recording_status()
    
    def start_manual_recording_with_check(self, camera_ids: List[int] = None) -> dict:
        """리소스 체크 후 수동 녹화 시작"""
        # 시스템 과부하 확인
        if self.resource_monitor.is_system_overloaded():
            return {
                "success": False,
                "reason": "system_overload",
                "message": "시스템 과부하로 인해 수동 녹화를 시작할 수 없습니다",
                "recommendation": self.resource_monitor.get_recording_recommendation()
            }
        
        # 녹화 시작
        success = self.start_manual_recording(camera_ids)
        return {
            "success": success,
            "reason": "started" if success else "failed",
            "message": "수동 녹화가 시작되었습니다" if success else "수동 녹화 시작 실패",
            "system_status": self.resource_monitor.get_system_status()
        }
    
    def init_camera(self, camera_num: int) -> bool:
        """카메라 초기화 및 공유 스트림 준비"""
        if camera_num == 0 and not self.camera0_available:
            return False
        elif camera_num == 1 and not self.camera1_available:
            return False
        elif camera_num not in [0, 1]:
            return False
            
        # 공유 스트림 매니저 생성 (아직 스트림 시작하지 않음)
        if camera_num not in self.shared_streams:
            self.shared_streams[camera_num] = SharedStreamManager(camera_num, self)
            
        return True
    
    def capture_single_frame(self, camera_num: int) -> Optional[bytes]:
        """단일 프레임 캡처 (스냅샷용)"""
        if not self.init_camera(camera_num):
            return None
        
        try:
            with tempfile.NamedTemporaryFile(suffix='.jpg') as tmp_file:
                cmd = [
                    "rpicam-still",
                    "--camera", str(camera_num),
                    "--width", "640",
                    "--height", "480",
                    "-o", tmp_file.name,
                    "-t", "100",
                    "--nopreview"
                ]
                
                result = subprocess.run(cmd, capture_output=True, timeout=5)
                
                if result.returncode == 0:
                    with open(tmp_file.name, 'rb') as f:
                        return f.read()
                        
        except Exception as e:
            print(f"프레임 캡처 오류 (카메라 {camera_num}): {e}")
        
        return None
    
    def _start_rpicam_vid_stream(self, camera_num: int) -> subprocess.Popen:
        """rpicam-vid 스트림 프로세스 시작"""
        cmd = [
            "rpicam-vid",
            "--camera", str(camera_num),
            "--width", "640",
            "--height", "480",
            "--framerate", "30",
            "--codec", "mjpeg",
            "--output", "-",
            "--timeout", "0",  # 무한 실행
            "--nopreview"
        ]
        
        print(f"🎬 rpicam-vid 시작: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )
        
        return process
    
    def generate_mjpeg_stream(self, camera_num: int) -> Generator[bytes, None, None]:
        """공유 MJPEG 스트림 생성기 (다중 클라이언트 지원)"""
        if not self.init_camera(camera_num):
            print(f"❌ 카메라 {camera_num} 초기화 실패")
            return
            
        shared_stream = self.shared_streams[camera_num]
        
        # 공유 스트림이 실행 중이 아니면 시작
        if not shared_stream.is_running:
            if not shared_stream.start_stream():
                print(f"❌ 공유 스트림 시작 실패 (카메라 {camera_num})")
                return
        
        # 클라이언트 추가
        client_id = shared_stream.add_client()
        
        try:
            # 클라이언트별 스트림 제공
            yield from shared_stream.get_client_stream(client_id)
        except Exception as e:
            print(f"클라이언트 스트림 오류 (카메라 {camera_num}, {client_id[:8]}...): {e}")
        finally:
            # 클라이언트 제거 (자동으로 수행됨)
            print(f"🛑 클라이언트 스트림 종료 (카메라 {camera_num})")
    
    def stop_stream(self, camera_num: int) -> bool:
        """공유 스트림 중지 (모든 클라이언트 연결 해제)"""
        if camera_num in self.shared_streams:
            self.shared_streams[camera_num].stop_stream()
            print(f"✅ 카메라 {camera_num}번 공유 스트림 중지 요청")
            return True
        return False
    
    def capture_snapshot(self, camera_num: int, resolution: str = "hd") -> Optional[str]:
        """스냅샷 캡처 (해상도 선택 가능)"""
        if not self.init_camera(camera_num):
            return None
        
        # 해상도 설정
        resolution_presets = {
            "vga": {"width": 640, "height": 480, "folder": "640x480"},
            "hd": {"width": 1280, "height": 720, "folder": "1280x720"}, 
            "fhd": {"width": 1920, "height": 1080, "folder": "1920x1080"}
        }
        
        if resolution not in resolution_presets:
            resolution = "hd"  # 기본값
            
        res_config = resolution_presets[resolution]
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 해상도별 폴더 생성
            res_folder = self.snapshot_dir / res_config["folder"]
            res_folder.mkdir(parents=True, exist_ok=True)
            
            filename = f"camera{camera_num}_{timestamp}_{resolution}.jpg"
            filepath = res_folder / filename
            
            # 항상 rpicam-still을 사용하여 지정된 해상도로 캡처
            cmd = [
                "rpicam-still",
                "--camera", str(camera_num),
                "--width", str(res_config["width"]),
                "--height", str(res_config["height"]),
                "-o", str(filepath),
                "-t", "100",
                "--nopreview"
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            
            if result.returncode == 0 and filepath.exists():
                print(f"📸 스냅샷 저장 ({res_config['width']}×{res_config['height']}): {filename}")
                return f"{res_config['folder']}/{filename}"  # 폴더 포함 경로 반환
                
        except Exception as e:
            print(f"스냅샷 캡처 오류 (카메라 {camera_num}): {e}")
        
        return None
    
    def get_camera_status(self) -> dict:
        """카메라 상태 반환 (공유 스트림 기반)"""
        def get_stream_info(camera_num: int) -> dict:
            if camera_num in self.shared_streams:
                stream = self.shared_streams[camera_num]
                return {
                    "available": (camera_num == 0 and self.camera0_available) or 
                               (camera_num == 1 and self.camera1_available),
                    "streaming": stream.is_running,
                    "clients": len(stream.clients),
                    "fps": 30 if stream.is_running else 0
                }
            else:
                return {
                    "available": (camera_num == 0 and self.camera0_available) or 
                               (camera_num == 1 and self.camera1_available),
                    "streaming": False,
                    "clients": 0,
                    "fps": 0
                }
        
        # 연속 녹화 상태 추가
        continuous_status = {}
        for camera_id, recorder in self.continuous_recorders.items():
            continuous_status[f"continuous_rec_cam{camera_id}"] = recorder.get_recording_status()
        
        # 수동 녹화 상태 추가
        manual_status = self.get_manual_recording_status()
        
        # 시스템 리소스 상태 추가
        system_status = self.resource_monitor.get_system_status()
        recording_recommendation = self.resource_monitor.get_recording_recommendation()
        
        return {
            "camera0": get_stream_info(0),
            "camera1": get_stream_info(1),
            "is_recording": manual_status.get("is_recording", False),  # 수동 녹화 상태로 업데이트
            "continuous_recording": continuous_status,
            "manual_recording": manual_status,
            "system": system_status,
            "recording_recommendation": recording_recommendation
        }
    
    def _restart_camera(self, camera_id: int):
        """카메라 자동 재시작 기능"""
        try:
            print(f"🔄 카메라 {camera_id} 자동 재시작 시작...")
            
            # 기존 스트림 정리
            if camera_id in self.shared_streams:
                self.shared_streams[camera_id].stop_stream()
                time.sleep(2)  # 정리 시간 대기
            
            # 카메라 재감지
            print(f"🔍 카메라 {camera_id} 하드웨어 재감지...")
            self._detect_cameras()
            
            # 카메라 사용 가능성 확인
            is_available = (camera_id == 0 and self.camera0_available) or (camera_id == 1 and self.camera1_available)
            
            if not is_available:
                print(f"❌ 카메라 {camera_id} 하드웨어 재감지 실패 - 물리적 연결 확인 필요")
                return False
            
            # 새로운 스트림 매니저 생성
            print(f"🔧 카메라 {camera_id} 새 스트림 매니저 생성...")
            self.shared_streams[camera_id] = SharedStreamManager(camera_id, self)
            
            # 잠시 대기 후 자동 초기화 시도
            time.sleep(1)
            success = self.init_camera(camera_id)
            
            if success:
                print(f"✅ 카메라 {camera_id} 자동 재시작 성공")
                return True
            else:
                print(f"❌ 카메라 {camera_id} 자동 재시작 실패")
                return False
                
        except Exception as e:
            print(f"❌ 카메라 {camera_id} 재시작 중 오류: {e}")
            return False
    
    def get_camera_health_status(self):
        """카메라 헬스 상태 확인"""
        health_status = {}
        for camera_id, stream in self.shared_streams.items():
            health_status[f"camera{camera_id}"] = {
                "is_healthy": stream.is_healthy,
                "retry_count": stream.retry_count,
                "last_error_time": stream.last_error_time,
                "is_running": stream.is_running
            }
        return health_status
    
    def cleanup(self):
        """리소스 정리 (모든 공유 스트림 및 연속 녹화 중지)"""
        print("🧹 블랙박스 카메라 매니저 정리 중...")
        
        # 모든 공유 스트림 중지
        for camera_num, shared_stream in list(self.shared_streams.items()):
            shared_stream.stop_stream()
        
        # 모든 연속 녹화 중지
        for camera_id, recorder in list(self.continuous_recorders.items()):
            recorder.stop_continuous_recording()
        
        # 수동 녹화 중지
        if self.manual_recorder:
            self.manual_recorder.stop_manual_recording()
        
        self.shared_streams.clear()
        self.continuous_recorders.clear()
        print("✅ 모든 스트림, 연속 녹화 및 수동 녹화 정리 완료")

# 전역 인스턴스
camera_manager = CameraManager()

if __name__ == "__main__":
    """테스트 실행"""
    print("🧪 카메라 매니저 테스트 (30 FPS)")
    
    # 카메라 상태 확인
    status = camera_manager.get_camera_status()
    print(f"카메라 상태: {status}")
    
    # 스냅샷 테스트
    if status["camera0"]["available"]:
        print("\n📸 카메라 0번 스냅샷 테스트")
        snap0 = camera_manager.capture_snapshot(0)
        if snap0:
            print(f"   저장됨: {snap0}")
    
    if status["camera1"]["available"]:
        print("\n📸 카메라 1번 스냅샷 테스트")
        snap1 = camera_manager.capture_snapshot(1)
        if snap1:
            print(f"   저장됨: {snap1}")
    
    print("\n🎉 테스트 완료")