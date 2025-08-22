class CCTVSystem {
  constructor() {
    this.cameras = {
      0: { stream: null, recording: false, backendId: 0 }, // Frontend Camera 1 → Backend 0
      1: { stream: null, recording: false, backendId: 1 }, // Frontend Camera 2 → Backend 1
    }
    this.mediaRecorders = {}
    this.recordingStartTime = null
    this.recordingTimer = null
    this.videoFiles = []
    this.imageFiles = []

    this.init()
  }

  init() {
    this.updateFileCounts()
    this.loadSavedFiles()
    this.setupCameraStreams()
    
    // 스트림 우선 모드: 자동으로 스트림 시작
    setTimeout(() => {
      console.log('📺 스트림 우선 모드: 자동 스트림 시작...');
      this.autoConnectCameras();
    }, 2000);
  }
  
  showTestModeIndicator() {
    // 페이지 상단에 테스트 모드 표시
    const header = document.querySelector('.header');
    if (header) {
      const testBanner = document.createElement('div');
      testBanner.style.cssText = `
        background: #ff6b35; 
        color: white; 
        text-align: center; 
        padding: 8px; 
        font-weight: bold;
        margin-bottom: 10px;
        border-radius: 4px;
      `;
      testBanner.textContent = '🚀 30 FPS 테스트 모드 (포트 8001)';
      header.insertAdjacentElement('afterend', testBanner);
    }
  }
  
  async autoConnectCameras() {
    try {
      console.log('🚀 카메라 1 자동 연결 시도 (30 FPS)...');
      await this.startCamera(0);
      
      setTimeout(async () => {
        console.log('🚀 카메라 2 자동 연결 시도 (30 FPS)...');
        await this.startCamera(1);
      }, 1000);
    } catch (error) {
      console.error('30 FPS 자동 연결 실패:', error);
    }
  }

  setupCameraStreams() {
    // 듀얼 카메라 상태 확인
    console.log('🚀 30 FPS 듀얼 카메라 시스템 초기화 중...');
    
    fetch('/api/camera/status')
      .then(response => response.json())
      .then(data => {
        console.log('🚀 초기 30 FPS 듀얼 카메라 상태:', data);
        
        // 테스트 모드 확인
        if (data.test_mode) {
          console.log('✅ 30 FPS 테스트 모드 확인됨');
        }
        
        // 각 카메라 상태 표시
        this.updateCameraStatus(1, data.camera0?.available || false, data.camera0?.fps || 0);
        this.updateCameraStatus(2, data.camera1?.available || false, data.camera1?.fps || 0);
        
        console.log('🚀 30 FPS 듀얼 카메라 시스템 초기화 완료 - 연결 버튼을 클릭하여 카메라를 연결하세요');
      })
      .catch(error => {
        console.error('30 FPS 듀얼 카메라 상태 확인 실패:', error);
        console.log('🚀 30 FPS 듀얼 카메라 시스템 초기화 완료 - 연결 버튼을 클릭하여 카메라를 연결하세요');
      });
  }

  updateCameraStatus(cameraId, available, fps = 0) {
    const status = document.getElementById(`camera${cameraId}-status`);
    if (!status) {
      console.warn(`Status element not found for camera ${cameraId}`);
      return;
    }
    
    if (available) {
      const fpsText = fps > 0 ? ` (${fps} FPS)` : '';
      status.innerHTML = `<div class="status-dot"></div>사용 가능${fpsText}`;
      status.className = 'camera-status';
    } else {
      status.innerHTML = '<div class="status-dot offline"></div>카메라 없음';
      status.className = 'camera-status';
    }
  }

  checkCameraStatus() {
    // 카메라 1 스트림 상태 확인
    const camera1Stream = document.getElementById('camera1-stream');
    if (camera1Stream.complete && camera1Stream.naturalWidth > 0) {
      // 이미지가 로드되었고 유효한 크기를 가지면 연결된 것으로 간주
      if (!this.cameras[1].stream) {
        this.handleStreamLoad(1);
      }
    }
  }

  handleStreamLoad(cameraId) {
    const overlay = document.getElementById(`camera${cameraId}-overlay`);
    const status = document.getElementById(`camera${cameraId}-status`);
    
    overlay.classList.add('hidden');
    status.innerHTML = '<div class="status-dot"></div>연결됨 (30 FPS)';
    status.className = 'camera-status online';
    this.cameras[cameraId].stream = 'connected';
    
    console.log(`🚀 카메라 ${cameraId} 30 FPS 스트림 로드 성공`);
  }

  handleStreamError(cameraId) {
    const stream = document.getElementById(`camera${cameraId}-stream`);
    const overlay = document.getElementById(`camera${cameraId}-overlay`);
    const status = document.getElementById(`camera${cameraId}-status`);

    stream.style.display = 'none';
    overlay.classList.remove('hidden');
    
    status.innerHTML = '<div class="status-dot offline"></div>30 FPS 연결 실패';
    overlay.innerHTML = `
      <div class="camera-icon">📹</div>
      <p>카메라 ${cameraId} 30 FPS 연결에 실패했습니다</p>
      <p style="font-size: 12px; margin-top: 8px;">• 카메라가 연결되었는지 확인하세요</p>
      <p style="font-size: 12px;">• rpicam-vid가 설치되었는지 확인하세요</p>
    `;
    
    status.className = 'camera-status';
    this.cameras[cameraId].stream = null;
  }

  async startCamera(cameraId) {
    const stream = document.getElementById(`camera${cameraId}-stream`);
    const overlay = document.getElementById(`camera${cameraId}-overlay`);
    const status = document.getElementById(`camera${cameraId}-status`);
    const backendId = this.cameras[cameraId].backendId;

    // 상태 업데이트
    status.innerHTML = '<div class="status-dot"></div>30 FPS 연결 중...';
    status.className = 'camera-status';
    
    try {
      // Backend에 카메라 연결 요청
      const response = await fetch(`/api/camera/${backendId}/connect`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log(`🚀 카메라 ${cameraId} (백엔드 ${backendId}) 30 FPS 연결 성공:`, data);
        
        // MJPEG 스트림 연결
        this.initializeMJPEGStream(cameraId, backendId);
        
        this.showToast(`카메라 ${cameraId} 30 FPS 연결 성공`, 'success');
      } else {
        throw new Error(`카메라 ${cameraId} 30 FPS 연결 실패`);
      }
    } catch (error) {
      console.error(`카메라 ${cameraId} 30 FPS 연결 오류:`, error);
      this.handleStreamError(cameraId);
      this.showError(`카메라 ${cameraId} 30 FPS 연결에 실패했습니다`);
    }
  }

  initializeMJPEGStream(cameraId, backendId) {
    console.log(`🚀 30 FPS MJPEG 스트림 초기화: 카메라 ${cameraId} (백엔드 ${backendId})`);
    const img = document.getElementById(`camera${cameraId}-stream`);
    
    // MJPEG 스트림 URL
    const streamUrl = `/video_feed/${backendId}`;
    console.log(`🚀 카메라 ${cameraId} 30 FPS 스트림 URL:`, streamUrl);
    
    // 이미지 이벤트 리스너
    img.onload = () => {
      console.log(`🚀 카메라 ${cameraId} 30 FPS MJPEG 스트림 로드 성공`);
      this.handleStreamLoad(cameraId);
    };
    
    img.onerror = (e) => {
      console.error(`카메라 ${cameraId} 30 FPS MJPEG 스트림 로드 실패:`, e);
      this.handleStreamError(cameraId);
    };
    
    // MJPEG 스트림 설정
    img.src = streamUrl;
    img.style.display = 'block';
  }

  async stopCamera(cameraId) {
    const img = document.getElementById(`camera${cameraId}-stream`);
    const overlay = document.getElementById(`camera${cameraId}-overlay`);
    const status = document.getElementById(`camera${cameraId}-status`);
    const backendId = this.cameras[cameraId].backendId;

    try {
      // Backend에 카메라 연결 해제 요청
      const response = await fetch(`/api/camera/${backendId}/disconnect`, {
        method: 'POST'
      });
      
      if (response.ok) {
        console.log(`🚀 카메라 ${cameraId} (백엔드 ${backendId}) 30 FPS 연결 해제 성공`);
        this.showToast(`카메라 ${cameraId} 30 FPS 연결 해제`, 'info');
      }
    } catch (error) {
      console.error(`카메라 ${cameraId} 30 FPS 연결 해제 오류:`, error);
    }

    // UI 업데이트
    img.src = '';
    img.style.display = 'none';
    overlay.classList.remove('hidden');
    status.innerHTML = '<div class="status-dot offline"></div>연결 대기중';
    status.className = 'camera-status';
    
    this.cameras[cameraId].stream = null;
    console.log(`🚀 카메라 ${cameraId} 30 FPS 스트림 중지됨`);
  }

  async captureSnapshot(cameraId) {
    const backendId = this.cameras[cameraId].backendId;
    
    if (!this.cameras[cameraId].stream) {
      this.showError(`카메라 ${cameraId}가 연결되지 않았습니다.`);
      return;
    }

    // 선택된 해상도 가져오기
    const resolutionSelect = document.getElementById(`camera${cameraId}-resolution`);
    const resolution = resolutionSelect.value;
    
    const resolutionNames = {
      'vga': '640×480',
      'hd': '1280×720', 
      'fhd': '1920×1080'
    };

    try {
      const response = await fetch(`/api/snapshot/${backendId}?resolution=${resolution}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        this.showToast(`카메라 ${cameraId} 스냅샷 저장 (${resolutionNames[resolution]}): ${data.data.filename}`, 'success');
        this.refreshFileList();
      } else {
        throw new Error('스냅샷 캡처 실패');
      }
    } catch (error) {
      console.error('스냅샷 오류:', error);
      this.showError('스냅샷 캡처에 실패했습니다');
    }
  }

  async toggleRecording() {
    const recordBtn = document.getElementById('recordBtn');
    const recordingStatus = document.getElementById('recordingStatus');
    
    // 현재 녹화 상태 확인
    const statusResponse = await fetch('/api/recording/status');
    const status = await statusResponse.json();
    
    if (status.is_recording) {
      // 녹화 중지
      await this.stopRecording();
    } else {
      // 녹화 시작
      await this.startRecording();
    }
  }

  async startRecording() {
    try {
      const response = await fetch('/api/recording/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        this.showToast(`수동 녹화가 시작되었습니다 (1920×1080)`, 'success');
        
        // Update UI
        Object.keys(this.cameras).forEach((id) => {
          if (this.cameras[id].stream) {
            this.cameras[id].recording = true;
          }
        });

        this.recordingStartTime = Date.now();
        this.startRecordingTimer();
        this.updateRecordingUI(true);
      } else {
        throw new Error('수동 녹화 시작 실패');
      }
    } catch (error) {
      console.error('수동 녹화 오류:', error);
      this.showError('수동 녹화 시작 실패: ' + error.message);
    }
  }

  async stopRecording() {
    try {
      const response = await fetch('/api/recording/stop', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        this.showToast(`수동 녹화가 중지되었습니다: ${data.data.file_count}개 파일`, 'success');
        
        Object.keys(this.cameras).forEach((id) => {
          this.cameras[id].recording = false;
        });

        this.stopRecordingTimer();
        this.updateRecordingUI(false);
        this.refreshFileList();
      } else {
        throw new Error('수동 녹화 정지 실패');
      }
    } catch (error) {
      console.error('수동 녹화 정지 오류:', error);
      this.showError('수동 녹화 정지에 실패했습니다');
    }
  }

  startRecordingTimer() {
    this.recordingTimer = setInterval(() => {
      const elapsed = Date.now() - this.recordingStartTime;
      const minutes = Math.floor(elapsed / 60000);
      const seconds = Math.floor((elapsed % 60000) / 1000);

      document.getElementById('recordingTime').textContent =
        `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }, 1000);
  }

  stopRecordingTimer() {
    if (this.recordingTimer) {
      clearInterval(this.recordingTimer);
      this.recordingTimer = null;
    }
    document.getElementById('recordingTime').textContent = '00:00';
  }

  updateRecordingUI(isRecording) {
    const recordBtn = document.getElementById('recordBtn');
    const recordingStatus = document.getElementById('recordingStatus');

    if (isRecording) {
      recordBtn.innerHTML = '<span class="record-icon">⏹</span>긴 영상 중지';
      recordBtn.classList.add('recording');
      recordingStatus.textContent = '수동 녹화 중 (640×480)';
    } else {
      recordBtn.innerHTML = '<span class="record-icon">⏺</span>긴 영상 녹화';
      recordBtn.classList.remove('recording');
      recordingStatus.textContent = '대기중';
    }
  }

  async refreshFileList() {
    try {
      const response = await fetch('/api/files');
      if (response.ok) {
        const files = await response.json();
        this.displayFiles(files);
      } else {
        throw new Error('파일 목록 로드 실패');
      }
    } catch (error) {
      console.error('파일 목록 오류:', error);
      this.showError('파일 목록을 불러올 수 없습니다');
    }
  }

  displayFiles(files) {
    // 비디오 파일 표시
    const videoList = document.getElementById('videoList');
    const imageList = document.getElementById('imageList');
    
    const videoFiles = files.filter(file => file.file_type === 'video');
    const imageFiles = files.filter(file => file.file_type === 'image');
    
    this.updateVideoList(videoFiles);
    this.updateImageList(imageFiles);
    this.updateFileCounts(videoFiles.length, imageFiles.length);
  }

  updateVideoList(videoFiles) {
    const videoList = document.getElementById('videoList');
    
    if (videoFiles.length === 0) {
      videoList.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🎥</div>
          <p>30 FPS 녹화된 동영상이 없습니다</p>
        </div>
      `;
    } else {
      videoList.innerHTML = videoFiles
        .map(file => `
          <div class="file-item">
            <div class="file-info">
              <div class="file-name">${file.filename}</div>
              <div class="file-meta">${this.formatFileSize(file.size)} • ${this.formatDateTime(file.created_at)}</div>
            </div>
            <div class="file-actions">
              <button class="btn btn-small btn-secondary" onclick="cctvSystem.downloadFile('videos', '${file.filename}')">다운로드</button>
              <button class="btn btn-small btn-secondary" onclick="cctvSystem.deleteFile('videos', '${file.filename}')">삭제</button>
            </div>
          </div>
        `)
        .join('');
    }
  }

  updateImageList(imageFiles) {
    const imageList = document.getElementById('imageList');
    
    if (imageFiles.length === 0) {
      imageList.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📷</div>
          <p>30 FPS 캡처된 이미지가 없습니다</p>
        </div>
      `;
    } else {
      imageList.innerHTML = imageFiles
        .map(file => `
          <div class="file-item">
            <div class="file-info">
              <div class="file-name">${file.filename}</div>
              <div class="file-meta">${this.formatFileSize(file.size)} • ${this.formatDateTime(file.created_at)}</div>
            </div>
            <div class="file-actions">
              <button class="btn btn-small btn-secondary" onclick="cctvSystem.downloadFile('images', '${file.filename}')">다운로드</button>
              <button class="btn btn-small btn-secondary" onclick="cctvSystem.deleteFile('images', '${file.filename}')">삭제</button>
            </div>
          </div>
        `)
        .join('');
    }
  }

  downloadFile(fileType, filename) {
    console.log('30 FPS 파일 다운로드:', filename);
    const url = `/api/files/${fileType}/${filename}`;
    
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    this.showToast('30 FPS 파일 다운로드를 시작합니다', 'info');
  }

  async deleteFile(fileType, filename) {
    if (!confirm(`'${filename}' 30 FPS 파일을 삭제하시겠습니까?`)) {
      return;
    }
    
    console.log('30 FPS 파일 삭제:', filename);
    
    try {
      const response = await fetch(`/api/files/${fileType}/${filename}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        this.showToast('30 FPS 파일이 삭제되었습니다', 'success');
        this.refreshFileList();
      } else {
        throw new Error('30 FPS 파일 삭제 실패');
      }
    } catch (error) {
      console.error('30 FPS 파일 삭제 오류:', error);
      this.showError('30 FPS 파일 삭제에 실패했습니다');
    }
  }

  updateFileCounts(videoCount = null, imageCount = null) {
    if (videoCount !== null) {
      document.getElementById('videoCount').textContent = `${videoCount}개`;
    }
    if (imageCount !== null) {
      document.getElementById('imageCount').textContent = `${imageCount}개`;
    }
  }

  showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    
    setTimeout(() => {
      toast.classList.add('show');
    }, 100);
    
    setTimeout(() => {
      toast.classList.remove('show');
    }, 3100);
  }

  showError(message) {
    this.showToast(message, 'error');
  }

  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Number.parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  formatDateTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }

  async toggleContinuousRecording(cameraId) {
    const button = document.getElementById(`camera${cameraId}-record-btn`);
    const backendId = this.cameras[cameraId].backendId;
    
    try {
      // 현재 연속 녹화 상태 확인
      const statusResponse = await fetch(`/api/camera/${backendId}/continuous_status`);
      const status = await statusResponse.json();
      
      if (status.is_recording) {
        // 연속 녹화 중지
        const response = await fetch(`/api/camera/${backendId}/stop_continuous`, {
          method: 'POST'
        });
        
        if (response.ok) {
          button.textContent = '●REC 시작';
          button.className = 'btn btn-primary';
          this.showToast(`카메라 ${cameraId + 1} 블랙박스 중지, 스트림 재시작`, 'info');
        }
      } else {
        // 연속 녹화 시작
        const response = await fetch(`/api/camera/${backendId}/start_continuous`, {
          method: 'POST'
        });
        
        if (response.ok) {
          button.textContent = '⏹ 블랙박스 중지';
          button.className = 'btn btn-danger';
          this.showToast(`카메라 ${cameraId + 1} 블랙박스 시작 (640×480, 30초 세그먼트)`, 'success');
        }
      }
    } catch (error) {
      console.error('연속 녹화 토글 오류:', error);
      this.showError('연속 녹화 제어에 실패했습니다');
    }
  }

  loadSavedFiles() {
    // localStorage에서 파일 목록 로드 (기존 기능 유지)
    // 실제 API에서 파일 목록을 가져오므로 여기서는 빈 구현
  }
}

// 전역 함수들 (HTML onclick 핸들러용)
let cctvSystem;

function handleStreamLoad(cameraId) {
  cctvSystem.handleStreamLoad(cameraId);
}

function handleStreamError(cameraId) {
  cctvSystem.handleStreamError(cameraId);
}

function startCamera(cameraId) {
  cctvSystem.startCamera(cameraId);
}

function stopCamera(cameraId) {
  cctvSystem.stopCamera(cameraId);
}

function captureSnapshot(cameraId) {
  cctvSystem.captureSnapshot(cameraId);
}

function toggleRecording() {
  cctvSystem.toggleRecording();
}

function toggleContinuousRecording(cameraId) {
  cctvSystem.toggleContinuousRecording(cameraId);
}

// 시스템 초기화
document.addEventListener('DOMContentLoaded', () => {
  cctvSystem = new CCTVSystem();
  console.log('🚀 Fabcam CCTV System (30 FPS) 초기화 완료');
});