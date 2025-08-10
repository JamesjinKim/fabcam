// 전역 변수
let isRecording = false;
let currentFilter = 'all';
let recordingStartTime = null;

// DOM 요소
const videoStream = document.getElementById('videoStream');
const streamError = document.getElementById('streamError');
const recordBtn = document.getElementById('recordBtn');
const recordingStatus = document.getElementById('recordingStatus');
const connectionStatus = document.getElementById('connectionStatus');
const filesList = document.getElementById('filesList');

// 초기화
document.addEventListener('DOMContentLoaded', function() {
    console.log('Fabcam CCTV System 초기화 중...');
    
    // 비디오 스트림 설정
    setupVideoStream();
    
    // 파일 목록 로드
    refreshFileList();
    
    // 녹화 상태 확인
    checkRecordingStatus();
    
    // 주기적으로 상태 확인 (5초마다)
    setInterval(checkRecordingStatus, 5000);
    
    console.log('초기화 완료');
});

// 비디오 스트림 설정
function setupVideoStream() {
    videoStream.onload = function() {
        console.log('비디오 스트림 연결됨');
        streamError.style.display = 'none';
        videoStream.style.display = 'block';
        updateConnectionStatus(true);
    };
    
    videoStream.onerror = function() {
        console.log('비디오 스트림 오류');
        handleStreamError();
    };
}

// 스트림 오류 처리
function handleStreamError() {
    console.log('스트림 오류 처리 중...');
    videoStream.style.display = 'none';
    streamError.style.display = 'flex';
    updateConnectionStatus(false);
}

// 스트림 재시도
function retryStream() {
    console.log('스트림 재시도 중...');
    const timestamp = new Date().getTime();
    videoStream.src = `/video_feed?t=${timestamp}`;
    streamError.style.display = 'none';
    videoStream.style.display = 'block';
}

// 연결 상태 업데이트
function updateConnectionStatus(connected) {
    if (connected) {
        connectionStatus.textContent = '연결됨';
        connectionStatus.className = 'status-connected';
    } else {
        connectionStatus.textContent = '연결 안됨';
        connectionStatus.className = 'status-disconnected';
    }
}

// 녹화 토글
async function toggleRecording() {
    console.log('녹화 토글:', isRecording ? '정지' : '시작');
    
    try {
        recordBtn.disabled = true;
        
        if (isRecording) {
            // 녹화 정지
            const response = await fetch('/api/recording/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                showToast('녹화가 정지되었습니다', 'success');
                updateRecordingUI(false);
                refreshFileList();
            } else {
                throw new Error('녹화 정지 실패');
            }
        } else {
            // 녹화 시작
            const response = await fetch('/api/recording/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                showToast(`녹화가 시작되었습니다: ${data.data.filename}`, 'success');
                updateRecordingUI(true);
            } else {
                throw new Error('녹화 시작 실패');
            }
        }
    } catch (error) {
        console.error('녹화 토글 오류:', error);
        showToast('녹화 조작에 실패했습니다', 'error');
    } finally {
        recordBtn.disabled = false;
    }
}

// 녹화 UI 업데이트
function updateRecordingUI(recording) {
    isRecording = recording;
    
    if (recording) {
        recordBtn.textContent = '⏹️ 녹화 정지';
        recordBtn.className = 'btn btn-record recording';
        recordingStatus.className = 'recording-status recording';
        recordingStartTime = new Date();
    } else {
        recordBtn.textContent = '📹 녹화 시작';
        recordBtn.className = 'btn btn-record';
        recordingStatus.className = 'recording-status';
        recordingStartTime = null;
    }
}

// 스냅샷 캡처
async function captureSnapshot() {
    console.log('스냅샷 캡처 중...');
    
    try {
        const snapshotBtn = document.getElementById('snapshotBtn');
        snapshotBtn.disabled = true;
        
        const response = await fetch('/api/snapshot', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            showToast(`스냅샷이 저장되었습니다: ${data.data.filename}`, 'success');
            refreshFileList();
        } else {
            throw new Error('스냅샷 캡처 실패');
        }
    } catch (error) {
        console.error('스냅샷 오류:', error);
        showToast('스냅샷 캡처에 실패했습니다', 'error');
    } finally {
        document.getElementById('snapshotBtn').disabled = false;
    }
}

// 녹화 상태 확인
async function checkRecordingStatus() {
    try {
        const response = await fetch('/api/recording/status');
        if (response.ok) {
            const data = await response.json();
            if (data.is_recording !== isRecording) {
                updateRecordingUI(data.is_recording);
            }
        }
    } catch (error) {
        console.error('녹화 상태 확인 오류:', error);
    }
}

// 파일 목록 새로고침
async function refreshFileList() {
    console.log('파일 목록 새로고침 중...');
    
    try {
        filesList.innerHTML = '<div class="loading">파일 목록을 불러오는 중...</div>';
        
        const response = await fetch('/api/files');
        if (response.ok) {
            const files = await response.json();
            displayFiles(files);
        } else {
            throw new Error('파일 목록 로드 실패');
        }
    } catch (error) {
        console.error('파일 목록 오류:', error);
        filesList.innerHTML = '<div class="empty-state"><p>파일 목록을 불러올 수 없습니다</p></div>';
        showToast('파일 목록을 불러올 수 없습니다', 'error');
    }
}

// 파일 목록 표시
function displayFiles(files) {
    if (!files || files.length === 0) {
        filesList.innerHTML = '<div class="empty-state"><p>저장된 파일이 없습니다</p></div>';
        return;
    }
    
    // 필터링
    let filteredFiles = files;
    if (currentFilter !== 'all') {
        filteredFiles = files.filter(file => file.file_type === currentFilter);
    }
    
    if (filteredFiles.length === 0) {
        filesList.innerHTML = '<div class="empty-state"><p>해당 유형의 파일이 없습니다</p></div>';
        return;
    }
    
    const html = filteredFiles.map(file => {
        const fileIcon = file.file_type === 'video' ? '🎬' : '📸';
        const fileSize = formatFileSize(file.size);
        const createdAt = formatDateTime(file.created_at);
        
        return `
            <div class="file-item">
                <div class="file-info">
                    <div class="file-name">${fileIcon} ${file.filename}</div>
                    <div class="file-meta">${fileSize} • ${createdAt}</div>
                </div>
                <div class="file-actions">
                    <button class="btn btn-small btn-download" onclick="downloadFile('${file.file_type}s', '${file.filename}')">
                        📥 다운로드
                    </button>
                    <button class="btn btn-small btn-delete" onclick="deleteFile('${file.file_type}s', '${file.filename}')">
                        🗑️ 삭제
                    </button>
                </div>
            </div>
        `;
    }).join('');
    
    filesList.innerHTML = html;
}

// 파일 필터
function showFiles(filter) {
    currentFilter = filter;
    
    // 탭 버튼 활성화 상태 업데이트
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    refreshFileList();
}

// 파일 다운로드
function downloadFile(fileType, filename) {
    console.log('파일 다운로드:', filename);
    const url = `/api/files/${fileType}/${filename}`;
    
    // 새 창에서 다운로드 링크 열기
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showToast('파일 다운로드를 시작합니다', 'info');
}

// 파일 삭제
async function deleteFile(fileType, filename) {
    if (!confirm(`'${filename}' 파일을 삭제하시겠습니까?`)) {
        return;
    }
    
    console.log('파일 삭제:', filename);
    
    try {
        const response = await fetch(`/api/files/${fileType}/${filename}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showToast('파일이 삭제되었습니다', 'success');
            refreshFileList();
        } else {
            throw new Error('파일 삭제 실패');
        }
    } catch (error) {
        console.error('파일 삭제 오류:', error);
        showToast('파일 삭제에 실패했습니다', 'error');
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

// 키보드 단축키
document.addEventListener('keydown', function(event) {
    if (event.ctrlKey || event.metaKey) {
        switch(event.key) {
            case 'r':
                event.preventDefault();
                toggleRecording();
                break;
            case 's':
                event.preventDefault();
                captureSnapshot();
                break;
            case 'l':
                event.preventDefault();
                refreshFileList();
                break;
        }
    }
});

console.log('Fabcam CCTV System 스크립트 로드 완료');