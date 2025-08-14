// 전역 변수
let camera1Recording = false;
let camera2Recording = false;
let camera1RecordingStartTime = null;
let camera2RecordingStartTime = null;

// 카메라 상태 관리
const cameraStates = {
    1: {
        available: false,
        streaming: false,
        recording: false,
        lastError: null,
        retryCount: 0,
        reconnectTimeout: null
    },
    2: {
        available: false,
        streaming: false,
        recording: false,
        lastError: null,
        retryCount: 0,
        reconnectTimeout: null
    }
};

// 현재 호스트 동적 감지 (원격 연결 지원)
const baseUrl = window.location.protocol + '//' + window.location.host;

// 설정
const CONFIG = {
    maxRetries: 5,
    retryDelay: 1000,
    healthCheckInterval: 10000,
    streamTimeout: 5000
};

// DOM 요소
const videoStream1 = document.getElementById('videoStream1');
const streamError1 = document.getElementById('streamError1');
const videoStream2 = document.getElementById('videoStream2');
const streamError2 = document.getElementById('streamError2');
const camera2Placeholder = document.getElementById('camera2Placeholder');

const recordBtn1 = document.getElementById('recordBtn1');
const recordBtn2 = document.getElementById('recordBtn2');
const recordingStatus1 = document.getElementById('recordingStatus1');
const recordingStatus2 = document.getElementById('recordingStatus2');
const recordingIndicator = document.getElementById('recordingIndicator');

const connectionStatus = document.getElementById('connectionStatus');
const connectionIcon = document.getElementById('connectionIcon');
const camera1StatusDot = document.getElementById('camera1StatusDot');
const camera1StatusText = document.getElementById('camera1StatusText');
const camera2StatusDot = document.getElementById('camera2StatusDot');
const camera2StatusText = document.getElementById('camera2StatusText');

const videoFilesList1 = document.getElementById('videoFilesList1');
const imageFilesList1 = document.getElementById('imageFilesList1');
const videoFilesList2 = document.getElementById('videoFilesList2');
const imageFilesList2 = document.getElementById('imageFilesList2');

const fullscreenModal = document.getElementById('fullscreenModal');
const fullscreenVideo = document.getElementById('fullscreenVideo');

// 초기화
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Fabcam CCTV System 초기화 중...');
    
    // DOM 완전 로드 대기 후 초기화
    setTimeout(async () => {
        try {
            // 병렬로 시스템 초기화
            await Promise.allSettled([
                initializeAllCameras(),
                refreshAllFileLists(),
                checkAllRecordingStatus()
            ]);
            
            // 주기적 상태 확인 시작
            startHealthMonitoring();
            
            // 아이콘 초기화
            lucide.createIcons();
            
            console.log('✅ 초기화 완료');
            updateSystemStatus('온라인');
            showToast('시스템 초기화 완료', 'success');
        } catch (error) {
            console.error('❌ 초기화 오류:', error);
            updateSystemStatus('오류');
            showToast('시스템 초기화 실패', 'error');
        }
    }, 100);
});

// 모든 카메라 초기화 (병렬 처리)
async function initializeAllCameras() {
    console.log('🎥 모든 카메라 초기화 시작...');
    
    const initPromises = [1, 2].map(cameraId => initializeCamera(cameraId));
    const results = await Promise.allSettled(initPromises);
    
    let successCount = 0;
    results.forEach((result, index) => {
        const cameraId = index + 1;
        if (result.status === 'fulfilled' && result.value) {
            successCount++;
            console.log(`✅ 카메라${cameraId} 초기화 성공`);
        } else {
            console.log(`❌ 카메라${cameraId} 초기화 실패:`, result.reason);
        }
    });
    
    updateConnectionStatus(successCount > 0);
    console.log(`📊 카메라 초기화 완료: ${successCount}/2 성공`);
    
    return successCount > 0;
}

// 개별 카메라 초기화
async function initializeCamera(cameraId) {
    console.log(`🔍 카메라${cameraId} 초기화 시작...`);
    
    try {
        // 카메라 가용성 확인
        const available = await checkCameraAvailability(cameraId);
        if (!available) {
            throw new Error(`카메라${cameraId} 사용 불가`);
        }
        
        // 스트림 설정
        await setupVideoStream(cameraId);
        
        // 상태 업데이트
        cameraStates[cameraId].available = true;
        cameraStates[cameraId].streaming = true;
        updateCameraStatus(cameraId, true);
        updateSystemStatus('온라인');
        
        return true;
    } catch (error) {
        console.error(`❌ 카메라${cameraId} 초기화 오류:`, error);
        cameraStates[cameraId].lastError = error.message;
        handleStreamError(cameraId);
        return false;
    }
}

// 카메라 가용성 확인
async function checkCameraAvailability(cameraId) {
    try {
        const response = await fetch(`${baseUrl}/api/recording/status/${cameraId}`, {
            method: 'GET',
            timeout: CONFIG.streamTimeout
        });
        return response.ok;
    } catch (error) {
        console.warn(`카메라${cameraId} 가용성 확인 실패:`, error);
        return false;
    }
}

// 개별 비디오 스트림 설정
async function setupVideoStream(cameraId) {
    const videoElement = cameraId === 1 ? videoStream1 : videoStream2;
    const errorElement = cameraId === 1 ? streamError1 : streamError2;
    const placeholderElement = cameraId === 2 ? camera2Placeholder : null;
    
    return new Promise((resolve, reject) => {
        // 에러 핸들러 설정
        videoElement.onerror = () => {
            console.log(`카메라${cameraId} 비디오 스트림 오류`);
            reject(new Error(`스트림 로드 실패`));
        };
        
        // 로드 핸들러 설정
        videoElement.onloadstart = () => {
            console.log(`📺 카메라${cameraId} 스트림 로드 시작`);
        };
        
        videoElement.onloadeddata = () => {
            console.log(`✅ 카메라${cameraId} 스트림 데이터 로드 완료`);
            
            // UI 업데이트
            errorElement.style.display = 'none';
            if (placeholderElement) placeholderElement.style.display = 'none';
            videoElement.style.display = 'block';
            
            resolve(true);
        };
        
        // 스트림 시작
        const timestamp = new Date().getTime();
        videoElement.src = `${baseUrl}/video_feed/${cameraId}?t=${timestamp}`;
        
        // 타임아웃 설정
        setTimeout(() => {
            if (videoElement.readyState === 0) {
                reject(new Error('스트림 연결 타임아웃'));
            }
        }, CONFIG.streamTimeout);
    });
}

// 스트림 오류 처리 (개선된 버전)
function handleStreamError(cameraId) {
    console.log(`❌ 카메라${cameraId} 스트림 오류 처리 중...`);
    
    // 상태 업데이트
    cameraStates[cameraId].streaming = false;
    cameraStates[cameraId].retryCount++;
    
    // UI 업데이트
    const videoElement = cameraId === 1 ? videoStream1 : videoStream2;
    const errorElement = cameraId === 1 ? streamError1 : streamError2;
    const placeholderElement = cameraId === 2 ? camera2Placeholder : null;
    
    videoElement.style.display = 'none';
    errorElement.style.display = 'flex';
    if (placeholderElement && cameraId === 2) {
        placeholderElement.style.display = 'none';
    }
    
    updateCameraStatus(cameraId, false);
    
    // 전체 연결 상태 확인
    const anyConnected = Object.values(cameraStates).some(state => state.streaming);
    updateConnectionStatus(anyConnected);
    
    // 자동 재연결 시도
    scheduleAutoRetry(cameraId);
}

// 자동 재연결 스케줄링
function scheduleAutoRetry(cameraId) {
    const state = cameraStates[cameraId];
    
    // 최대 재시도 횟수 확인
    if (state.retryCount >= CONFIG.maxRetries) {
        console.log(`⛔ 카메라${cameraId} 최대 재시도 횟수 초과`);
        showToast(`카메라${cameraId} 연결 실패 (최대 재시도 초과)`, 'error');
        return;
    }
    
    // 기존 타이머 정리
    if (state.reconnectTimeout) {
        clearTimeout(state.reconnectTimeout);
    }
    
    // 지수 백오프로 재연결 시도
    const delay = CONFIG.retryDelay * Math.pow(2, state.retryCount - 1);
    console.log(`⏰ 카메라${cameraId} ${delay}ms 후 재연결 시도 (${state.retryCount}/${CONFIG.maxRetries})`);
    
    state.reconnectTimeout = setTimeout(async () => {
        console.log(`🔄 카메라${cameraId} 자동 재연결 시도...`);
        try {
            await initializeCamera(cameraId);
        } catch (error) {
            console.error(`자동 재연결 실패:`, error);
        }
    }, delay);
}

// 스트림 재시도 (개선된 버전)
async function retryStream(cameraId) {
    console.log(`🔄 카메라${cameraId} 수동 재시도 중...`);
    
    // 재시도 카운터 리셋
    cameraStates[cameraId].retryCount = 0;
    
    // 기존 자동 재연결 타이머 정리
    if (cameraStates[cameraId].reconnectTimeout) {
        clearTimeout(cameraStates[cameraId].reconnectTimeout);
        cameraStates[cameraId].reconnectTimeout = null;
    }
    
    try {
        showToast(`카메라${cameraId} 재연결 시도 중...`, 'info');
        await initializeCamera(cameraId);
        showToast(`카메라${cameraId} 재연결 성공!`, 'success');
    } catch (error) {
        console.error(`수동 재연결 실패:`, error);
        showToast(`카메라${cameraId} 재연결 실패`, 'error');
    }
}

// 건강 상태 모니터링 시작
function startHealthMonitoring() {
    console.log('❤️ 카메라 건강 상태 모니터링 시작');
    
    // 주기적으로 모든 카메라 상태 확인
    setInterval(async () => {
        await Promise.allSettled([
            checkCameraHealth(1),
            checkCameraHealth(2),
            checkAllRecordingStatus()
        ]);
    }, CONFIG.healthCheckInterval);
}

// 개별 카메라 건강 상태 확인
async function checkCameraHealth(cameraId) {
    try {
        const available = await checkCameraAvailability(cameraId);
        const currentlyStreaming = cameraStates[cameraId].streaming;
        
        // 상태 불일치 감지 및 복구
        if (available && !currentlyStreaming) {
            console.log(`🔧 카메라${cameraId} 상태 불일치 감지 - 복구 시도`);
            await initializeCamera(cameraId);
        } else if (!available && currentlyStreaming) {
            console.log(`⚠️ 카메라${cameraId} 연결 끊김 감지`);
            handleStreamError(cameraId);
        }
    } catch (error) {
        console.error(`카메라${cameraId} 건강 상태 확인 오류:`, error);
    }
}

// 연결 상태 업데이트 (전체 시스템 상태)
function updateConnectionStatus(connected) {
    if (connected) {
        connectionStatus.textContent = '연결됨';
        connectionStatus.className = 'connection-badge badge-success';
        connectionIcon.setAttribute('data-lucide', 'wifi');
        connectionIcon.className = 'connection-icon';
    } else {
        connectionStatus.textContent = '연결 오류';
        connectionStatus.className = 'connection-badge badge-error';
        connectionIcon.setAttribute('data-lucide', 'wifi-off');
        connectionIcon.className = 'connection-icon disconnected';
    }
    
    // 아이콘 업데이트
    lucide.createIcons();
}

// 개별 카메라 상태 업데이트 (강화된 버전)
function updateCameraStatus(cameraId, connected) {
    const statusDot = document.getElementById(`camera${cameraId}StatusDot`);
    const statusText = document.getElementById(`camera${cameraId}StatusText`);
    
    if (!statusDot || !statusText) {
        console.error(`카메라${cameraId} 상태 UI 요소를 찾을 수 없습니다`);
        return;
    }
    
    // 상태 업데이트
    cameraStates[cameraId].streaming = connected;
    
    if (connected) {
        statusDot.className = 'status-dot status-online';
        statusText.textContent = '온라인';
        
        // 카메라2 특별 처리
        if (cameraId === 2) {
            if (camera2Placeholder) camera2Placeholder.style.display = 'none';
            if (videoStream2) videoStream2.style.display = 'block';
        }
        
        console.log(`✅ 카메라${cameraId} 상태: 온라인`);
    } else {
        statusDot.className = 'status-dot status-offline';
        statusText.textContent = cameraStates[cameraId].retryCount > 0 ? '재연결 중' : '오프라인';
        
        // 카메라2 특별 처리
        if (cameraId === 2) {
            const videoElement = videoStream2;
            if (videoElement && videoElement.style.display !== 'block') {
                if (camera2Placeholder) camera2Placeholder.style.display = 'flex';
            }
            if (streamError2 && streamError2.style.display !== 'flex') {
                if (videoElement) videoElement.style.display = 'none';
            }
        }
        
        console.log(`❌ 카메라${cameraId} 상태: 오프라인`);
    }
    
    // 전체 연결 상태 업데이트
    updateOverallConnectionStatus();
}

// 전체 연결 상태 업데이트
function updateOverallConnectionStatus() {
    const anyConnected = Object.values(cameraStates).some(state => state.streaming);
    const allConnected = Object.values(cameraStates).every(state => state.streaming);
    
    if (allConnected) {
        updateConnectionStatus(true);
        connectionStatus.textContent = '모든 카메라 연결됨';
    } else if (anyConnected) {
        updateConnectionStatus(true);
        connectionStatus.textContent = '일부 카메라 연결됨';
    } else {
        updateConnectionStatus(false);
        connectionStatus.textContent = '연결 오류';
    }
}

// 녹화 토글
async function toggleRecording(cameraId) {
    
    const isRecording = cameraId === 1 ? camera1Recording : camera2Recording;
    console.log(`카메라 ${cameraId} 녹화 토글:`, isRecording ? '정지' : '시작');
    
    try {
        const recordBtn = document.getElementById(`recordBtn${cameraId}`);
        recordBtn.disabled = true;
        
        if (isRecording) {
            // 녹화 정지
            const response = await fetch(`${baseUrl}/api/recording/stop/${cameraId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                showToast(`카메라 ${cameraId} 녹화가 정지되었습니다`, 'success');
                updateRecordingUI(cameraId, false);
                refreshFileList(cameraId);
            } else {
                throw new Error('녹화 정지 실패');
            }
        } else {
            // 녹화 시작
            const response = await fetch(`${baseUrl}/api/recording/start/${cameraId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                showToast(`카메라 ${cameraId} 녹화가 시작되었습니다: ${data.data.filename}`, 'success');
                updateRecordingUI(cameraId, true);
            } else {
                throw new Error('녹화 시작 실패');
            }
        }
    } catch (error) {
        console.error(`카메라 ${cameraId} 녹화 토글 오류:`, error);
        showToast(`카메라 ${cameraId} 녹화 조작에 실패했습니다`, 'error');
    } finally {
        document.getElementById(`recordBtn${cameraId}`).disabled = false;
    }
}

// 녹화 UI 업데이트
function updateRecordingUI(cameraId, recording) {
    const recordBtn = document.getElementById(`recordBtn${cameraId}`);
    const recordingStatus = document.getElementById(`recordingStatus${cameraId}`);
    
    // DOM 요소 존재 확인
    if (!recordBtn || !recordingStatus) {
        console.error(`카메라 ${cameraId} 녹화 UI 요소를 찾을 수 없습니다`);
        return;
    }
    
    if (cameraId === 1) {
        camera1Recording = recording;
        camera1RecordingStartTime = recording ? new Date() : null;
    } else if (cameraId === 2) {
        camera2Recording = recording;
        camera2RecordingStartTime = recording ? new Date() : null;
    }
    
    if (recording) {
        recordBtn.innerHTML = `<i data-lucide="square" class="btn-icon"></i>녹화 정지`;
        recordBtn.className = 'btn btn-primary btn-large recording';
        recordingStatus.style.display = 'block';
    } else {
        recordBtn.innerHTML = `<i data-lucide="video" class="btn-icon"></i>녹화 시작`;
        recordBtn.className = 'btn btn-primary btn-large';
        recordingStatus.style.display = 'none';
    }
    
    // 헤더 녹화 표시기 업데이트
    const anyRecording = camera1Recording || camera2Recording;
    recordingIndicator.style.display = anyRecording ? 'flex' : 'none';
    
    // 아이콘 업데이트
    lucide.createIcons();
}

// 스냅샷 캡처
async function captureSnapshot(cameraId) {
    
    // 카메라 상태 확인
    if (!cameraStates[cameraId].streaming) {
        showToast(`카메라${cameraId}가 스트리밍 중이 아닙니다`, 'error');
        return;
    }
    
    console.log(`📸 카메라${cameraId} 스냅샷 캡처 시작...`);
    
    try {
        const snapshotBtn = document.getElementById(`snapshotBtn${cameraId}`);
        snapshotBtn.disabled = true;
        
        const response = await fetch(`${baseUrl}/api/snapshot/${cameraId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            showToast(`카메라 ${cameraId} 스냅샷이 저장되었습니다: ${data.data.filename}`, 'success');
            refreshFileList(cameraId);
        } else {
            throw new Error('스냅샷 캡처 실패');
        }
    } catch (error) {
        console.error(`카메라 ${cameraId} 스냅샷 오류:`, error);
        showToast(`카메라 ${cameraId} 스냅샷 캡처에 실패했습니다`, 'error');
    } finally {
        document.getElementById(`snapshotBtn${cameraId}`).disabled = false;
    }
}

// 녹화 상태 확인 (병렬 처리)
async function checkAllRecordingStatus() {
    const promises = [1, 2].map(async (cameraId) => {
        try {
            const response = await fetch(`${baseUrl}/api/recording/status/${cameraId}`);
            if (response.ok) {
                const data = await response.json();
                const currentRecording = cameraId === 1 ? camera1Recording : camera2Recording;
                
                // 상태 동기화
                if (data.is_recording !== currentRecording) {
                    console.log(`🔄 카메라${cameraId} 녹화 상태 동기화: ${currentRecording} → ${data.is_recording}`);
                    updateRecordingUI(cameraId, data.is_recording);
                }
                
                // 상태 저장
                cameraStates[cameraId].recording = data.is_recording;
                
                return { cameraId, success: true, recording: data.is_recording };
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            console.error(`카메라${cameraId} 녹화 상태 확인 오류:`, error);
            return { cameraId, success: false, error: error.message };
        }
    });
    
    const results = await Promise.allSettled(promises);
    const successCount = results.filter(r => r.status === 'fulfilled' && r.value.success).length;
    
    if (successCount === 0) {
        console.warn('⚠️ 모든 카메라의 녹화 상태 확인 실패');
    }
    
    return results;
}

// 파일 목록 새로고침 (개선된 버전)
async function refreshFileList(cameraId) {
    console.log(`📁 카메라${cameraId} 파일 목록 새로고침 시작...`);
    
    const videoFilesList = document.getElementById(`videoFilesList${cameraId}`);
    const imageFilesList = document.getElementById(`imageFilesList${cameraId}`);
    
    // DOM 요소 존재 확인
    if (!videoFilesList || !imageFilesList) {
        console.error(`카메라${cameraId} 파일 목록 요소를 찾을 수 없습니다`);
        throw new Error('DOM 요소 없음');
    }
    
    try {
        // 로딩 상태 표시
        videoFilesList.innerHTML = '<div class="loading">📹 동영상 목록 로드 중...</div>';
        imageFilesList.innerHTML = '<div class="loading">📸 이미지 목록 로드 중...</div>';
        
        const response = await fetch(`${baseUrl}/api/files/${cameraId}`, {
            timeout: 10000
        });
        
        if (response.ok) {
            const files = await response.json();
            console.log(`✅ 카메라${cameraId} 파일 목록 로드 성공: ${files.length}개`);
            displayFiles(cameraId, files);
            
            return { success: true, fileCount: files.length };
        } else {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        
    } catch (error) {
        console.error(`❌ 카메라${cameraId} 파일 목록 오류:`, error);
        
        // 에러 UI 표시
        const errorHtml = '<div class="empty-state"><i data-lucide="alert-circle"></i><p>파일 목록을 불러올 수 없습니다</p><button class="btn btn-outline btn-small" onclick="refreshFileList(' + cameraId + ')">다시 시도</button></div>';
        
        videoFilesList.innerHTML = errorHtml;
        imageFilesList.innerHTML = errorHtml;
        
        // 아이콘 업데이트
        lucide.createIcons();
        
        throw error;
    }
}

// 모든 카메라 파일 목록 새로고침 (에러 처리 강화)
async function refreshAllFileLists() {
    console.log('📁 모든 카메라 파일 목록 새로고침 시작...');
    
    const promises = [1, 2].map(cameraId => 
        refreshFileList(cameraId).catch(error => {
            console.error(`카메라${cameraId} 파일 목록 새로고침 실패:`, error);
            return { cameraId, error: error.message };
        })
    );
    
    const results = await Promise.allSettled(promises);
    const successCount = results.filter(r => r.status === 'fulfilled' && !r.value?.error).length;
    
    console.log(`📊 파일 목록 새로고침 완료: ${successCount}/2 성공`);
    
    if (successCount > 0) {
        showToast('파일 목록 업데이트 완료', 'success');
    }
    
    return results;
}

// 파일 목록 표시
function displayFiles(cameraId, files) {
    // 파일을 타입별로 분리
    const videoFiles = files.filter(file => file.file_type === 'video');
    const imageFiles = files.filter(file => file.file_type === 'image');
    
    const videoFilesList = document.getElementById(`videoFilesList${cameraId}`);
    const imageFilesList = document.getElementById(`imageFilesList${cameraId}`);
    
    // DOM 요소 존재 확인
    if (!videoFilesList || !imageFilesList) {
        console.error(`카메라 ${cameraId} 파일 표시 요소를 찾을 수 없습니다`);
        return;
    }
    
    // 동영상 파일 표시
    if (videoFiles.length === 0) {
        videoFilesList.innerHTML = '<div class="empty-state"><i data-lucide="video"></i><p>저장된 동영상이 없습니다</p></div>';
    } else {
        const videoHtml = videoFiles.map(file => createFileItem(cameraId, file, 'video')).join('');
        videoFilesList.innerHTML = videoHtml;
    }
    
    // 이미지 파일 표시
    if (imageFiles.length === 0) {
        imageFilesList.innerHTML = '<div class="empty-state"><i data-lucide="image"></i><p>저장된 이미지가 없습니다</p></div>';
    } else {
        const imageHtml = imageFiles.map(file => createFileItem(cameraId, file, 'image')).join('');
        imageFilesList.innerHTML = imageHtml;
    }
    
    // 아이콘 업데이트
    lucide.createIcons();
}

// 파일 아이템 생성
function createFileItem(cameraId, file, type) {
    const fileSize = formatFileSize(file.size);
    const createdAt = formatDateTime(file.created_at);
    const iconName = type === 'video' ? 'video' : 'image';
    
    return `
        <div class="file-item">
            <div class="file-item-content">
                <div class="file-info">
                    <div class="file-name">
                        <i data-lucide="${iconName}"></i>
                        ${file.filename}
                    </div>
                    <div class="file-meta">${fileSize} • ${createdAt}</div>
                </div>
                <div class="file-actions">
                    <button class="action-btn download" onclick="downloadFile(${cameraId}, '${file.file_type}s', '${file.filename}')" title="다운로드">
                        <i data-lucide="download"></i>
                    </button>
                    <button class="action-btn delete" onclick="deleteFile(${cameraId}, '${file.file_type}s', '${file.filename}')" title="삭제">
                        <i data-lucide="trash-2"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
}

// 파일 다운로드 (개선된 버전)
function downloadFile(cameraId, fileType, filename) {
    console.log(`⬇️ 카메라${cameraId} 파일 다운로드 시작: ${filename}`);
    
    try {
        const url = `${baseUrl}/api/files/${cameraId}/${fileType}/${filename}`;
        
        // 다운로드 링크 생성
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.style.display = 'none';
        
        // 다운로드 실행
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        console.log(`📥 파일 다운로드 링크 생성: ${filename}`);
        showToast(`다운로드 시작: ${filename}`, 'info');
        
        // 다운로드 성공 확인 (간접적)
        setTimeout(() => {
            showToast('다운로드가 시작되었습니다', 'success');
        }, 1000);
        
    } catch (error) {
        console.error(`❌ 파일 다운로드 오류:`, error);
        showToast(`다운로드 실패: ${filename}`, 'error');
    }
}

// 파일 삭제 (개선된 버전)
async function deleteFile(cameraId, fileType, filename) {
    if (!confirm(`'${filename}' 파일을 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.`)) {
        return;
    }
    
    console.log(`🗑️ 카메라${cameraId} 파일 삭제 시작: ${filename}`);
    
    try {
        const response = await fetch(`${baseUrl}/api/files/${cameraId}/${fileType}/${filename}`, {
            method: 'DELETE',
            timeout: 10000
        });
        
        if (response.ok) {
            console.log(`✅ 파일 삭제 성공: ${filename}`);
            showToast(`파일 삭제됨: ${filename}`, 'success');
            
            // 비동기로 파일 목록 새로고침
            setTimeout(() => refreshFileList(cameraId), 500);
        } else {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
    } catch (error) {
        console.error(`❌ 카메라${cameraId} 파일 삭제 오류:`, error);
        showToast(`파일 삭제 실패: ${error.message}`, 'error');
    }
}

// 전체화면 열기
function openFullscreen(cameraId) {
    
    const videoSrc = cameraId === 1 ? videoStream1.src : videoStream2.src;
    if (!videoSrc) {
        showToast(`카메라 ${cameraId}가 연결되지 않았습니다`, 'error');
        return;
    }
    
    // HD 스트림 사용 (1920x1080@30fps)
    const timestamp = new Date().getTime();
    const hdVideoSrc = `${baseUrl}/video_feed_hd/${cameraId}?t=${timestamp}`;
    
    console.log(`전체화면 HD 스트림 시작: 카메라 ${cameraId} (1280x720@25fps)`);
    showToast(`HD 전체화면 모드 (1280x720@25fps)`, 'info');
    
    fullscreenVideo.src = hdVideoSrc;
    fullscreenModal.style.display = 'flex';
    
    // ESC 키로 닫기
    document.addEventListener('keydown', handleFullscreenEscape);
}

// 전체화면 닫기
async function closeFullscreen() {
    fullscreenModal.style.display = 'none';
    fullscreenVideo.src = '';
    
    // ESC 키 이벤트 제거
    document.removeEventListener('keydown', handleFullscreenEscape);
    
    // 일반 모드로 복구 (카메라 1과 2 모두)
    try {
        await Promise.all([
            fetch(`${baseUrl}/api/camera/1/normal_mode`, { method: 'POST' }),
            fetch(`${baseUrl}/api/camera/2/normal_mode`, { method: 'POST' })
        ]);
        console.log('일반 모드로 복구 완료');
        showToast('일반 모드로 전환됨 (640x480@25fps)', 'info');
    } catch (error) {
        console.error('일반 모드 복구 오류:', error);
    }
}

// ESC 키 처리
function handleFullscreenEscape(event) {
    if (event.key === 'Escape') {
        closeFullscreen();
    }
}

// 토스트 메시지 표시
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    
    // 토스트 표시
    setTimeout(() => {
        toast.classList.add('show');
    }, 100);
    
    // 3초 후 토스트 숨기기
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3100);
}

// 파일 크기 포맷팅
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 날짜/시간 포맷팅
function formatDateTime(isoString) {
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

// 키보드 단축키 (확장된 버전)
document.addEventListener('keydown', function(event) {
    // Ctrl/Cmd + 키 조합
    if (event.ctrlKey || event.metaKey) {
        switch(event.key) {
            case '1':
                event.preventDefault();
                if (event.shiftKey) {
                    // Ctrl+Shift+1: 카메라1 스냅샷
                    captureSnapshot(1);
                } else {
                    // Ctrl+1: 카메라1 녹화 토글
                    toggleRecording(1);
                }
                break;
            case '2':
                event.preventDefault();
                if (event.shiftKey) {
                    // Ctrl+Shift+2: 카메라2 스냅샷
                    captureSnapshot(2);
                } else {
                    // Ctrl+2: 카메라2 녹화 토글
                    toggleRecording(2);
                }
                break;
            case 'a':
                event.preventDefault();
                if (event.shiftKey) {
                    // Ctrl+Shift+A: 모든 카메라 스냅샷
                    Promise.allSettled([
                        captureSnapshot(1),
                        captureSnapshot(2)
                    ]).then(() => {
                        showToast('모든 카메라 스냅샷 완료', 'success');
                    });
                } else {
                    // Ctrl+A: 모든 카메라 녹화 토글
                    toggleAllRecording();
                }
                break;
            case 'r':
                event.preventDefault();
                // Ctrl+R: 카메라1 녹화 토글 (레거시 지원)
                toggleRecording(1);
                break;
            case 's':
                event.preventDefault();
                // Ctrl+S: 카메라1 스냅샷 (레거시 지원)
                captureSnapshot(1);
                break;
            case 'l':
                event.preventDefault();
                // Ctrl+L: 파일 목록 새로고침
                refreshAllFileLists();
                break;
            case 'f':
                event.preventDefault();
                // Ctrl+F: 카메라1 전체화면 토글
                if (fullscreenModal.style.display === 'flex') {
                    closeFullscreen();
                } else {
                    openFullscreen(1);
                }
                break;
        }
    }
    
    // ESC 키: 전체화면 닫기
    if (event.key === 'Escape') {
        if (fullscreenModal.style.display === 'flex') {
            closeFullscreen();
        }
    }
    
    // F11 키: 카메라1 전체화면 (기본)
    if (event.key === 'F11') {
        event.preventDefault();
        if (fullscreenModal.style.display === 'flex') {
            closeFullscreen();
        } else {
            openFullscreen(1);
        }
    }
    
    // F12 키: 카메라2 전체화면
    if (event.key === 'F12') {
        event.preventDefault();
        if (fullscreenModal.style.display === 'flex') {
            closeFullscreen();
        } else {
            openFullscreen(2);
        }
    }
});

// 모든 카메라 녹화 토글
async function toggleAllRecording() {
    console.log('🎬 모든 카메라 녹화 토글 시작...');
    
    const camera1Recording = cameraStates[1].recording;
    const camera2Recording = cameraStates[2].recording;
    
    // 하나라도 녹화 중이면 모두 정지, 아니면 모두 시작
    const shouldStop = camera1Recording || camera2Recording;
    const action = shouldStop ? '정지' : '시작';
    
    showToast(`모든 카메라 녹화 ${action} 중...`, 'info');
    
    try {
        const promises = [];
        
        // 카메라1 처리
        if (cameraStates[1].available) {
            if (shouldStop && camera1Recording) {
                promises.push(toggleRecording(1));
            } else if (!shouldStop && !camera1Recording) {
                promises.push(toggleRecording(1));
            }
        }
        
        // 카메라2 처리
        if (cameraStates[2].available) {
            if (shouldStop && camera2Recording) {
                promises.push(toggleRecording(2));
            } else if (!shouldStop && !camera2Recording) {
                promises.push(toggleRecording(2));
            }
        }
        
        const results = await Promise.allSettled(promises);
        const successCount = results.filter(r => r.status === 'fulfilled').length;
        
        if (successCount > 0) {
            showToast(`${successCount}개 카메라 녹화 ${action} 완료`, 'success');
        } else {
            showToast(`카메라 녹화 ${action} 실패`, 'error');
        }
        
    } catch (error) {
        console.error('모든 카메라 녹화 토글 오류:', error);
        showToast('모든 카메라 녹화 조작 실패', 'error');
    }
}

// 키보드 단축키 도움말 표시
function showKeyboardHelp() {
    const helpText = `
🎮 키보드 단축키 도움말

📹 녹화 제어:
• Ctrl+1: 카메라1 녹화 토글
• Ctrl+2: 카메라2 녹화 토글  
• Ctrl+A: 모든 카메라 녹화 토글

📸 스냅샷:
• Ctrl+Shift+1: 카메라1 스냅샷
• Ctrl+Shift+2: 카메라2 스냅샷
• Ctrl+Shift+A: 모든 카메라 스냅샷

🖥️ 전체화면:
• F11: 카메라1 전체화면
• F12: 카메라2 전체화면
• Ctrl+F: 카메라1 전체화면 토글
• ESC: 전체화면 닫기

📁 파일 관리:
• Ctrl+L: 파일 목록 새로고침

🎯 레거시 지원:
• Ctrl+R: 카메라1 녹화 (기존)
• Ctrl+S: 카메라1 스냅샷 (기존)
`;
    
    alert(helpText);
}

// 도움말 버튼 이벤트 (필요시 HTML에서 호출)
window.showKeyboardHelp = showKeyboardHelp;

// 전체 제어 패널 토글
function toggleGlobalControls() {
    const globalControls = document.getElementById('globalControls');
    const toggleIcon = globalControls.querySelector('.toggle-icon');
    
    globalControls.classList.toggle('collapsed');
    
    // 아이콘 업데이트
    if (globalControls.classList.contains('collapsed')) {
        toggleIcon.setAttribute('data-lucide', 'chevron-down');
    } else {
        toggleIcon.setAttribute('data-lucide', 'chevron-up');
    }
    
    lucide.createIcons();
}

// 모든 카메라 스냅샷 (전체 제어용)
async function captureAllSnapshots() {
    console.log('📸 모든 카메라 스냅샷 시작...');
    showToast('모든 카메라 스냅샷 촬영 중...', 'info');
    
    try {
        const promises = [1, 2].map(cameraId => {
            if (cameraStates[cameraId].streaming) {
                return captureSnapshot(cameraId);
            } else {
                return Promise.resolve({ cameraId, skipped: true });
            }
        });
        
        const results = await Promise.allSettled(promises);
        const successCount = results.filter(r => r.status === 'fulfilled').length;
        
        if (successCount > 0) {
            showToast(`${successCount}개 카메라 스냅샷 완료`, 'success');
        } else {
            showToast('스냅샷 촬영 실패', 'error');
        }
        
    } catch (error) {
        console.error('모든 카메라 스냅샷 오류:', error);
        showToast('스냅샷 촬영 실패', 'error');
    }
}

// 시스템 상태 업데이트
function updateSystemStatus(status) {
    const systemStatus = document.getElementById('systemStatus');
    const camerasOnline = document.getElementById('camerasOnline');
    
    if (systemStatus) {
        systemStatus.textContent = status;
    }
    
    if (camerasOnline) {
        const onlineCount = Object.values(cameraStates).filter(state => state.streaming).length;
        camerasOnline.textContent = `${onlineCount}/2`;
    }
}

// 전역 함수로 등록
window.toggleGlobalControls = toggleGlobalControls;
window.captureAllSnapshots = captureAllSnapshots;

console.log('Fabcam CCTV System 스크립트 로드 완료');