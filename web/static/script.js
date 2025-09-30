// SHT CCTV System - Dual View Support JavaScript - 중복 제거 버전

let currentViewMode = 'dual';  // 'dual', 'single'
let currentCamera = null;  // null (dual), 0, or 1
let currentResolution = '640x480';
let statsInterval = null;
let heartbeatInterval = null;
// Recording functionality removed - continuous recording handled by webmain.py
let isApiCallInProgress = false;  // API 호출 중복 방지

// AI 감지 관련 변수
let aiEnabled = false;
let aiStatsInterval = null;

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    console.log('[INIT] CCTV 시스템 초기화');

    // 듀얼 모드로 시작
    initializeDualMode();

    // 통계 업데이트 시작
    updateStats();
    statsInterval = setInterval(updateStats, 2000);

    // 하트비트 체크 시작
    checkStreamActivity();
    heartbeatInterval = setInterval(checkStreamActivity, 3000);

    // Continuous recording handled by GPURecorder in webmain.py
});

// 듀얼 모드 초기화
function initializeDualMode() {
    console.log('[INIT] 듀얼 모드 초기화 시작');

    // 기본적으로 듀얼 뷰 표시
    currentViewMode = 'dual';
    currentCamera = null;

    // UI 업데이트
    document.getElementById('dual-view').classList.remove('hidden');
    document.getElementById('single-view').classList.add('hidden');
    setActiveButton('dual-btn');

    // 안전한 요소 업데이트
    const currentCameraElement = document.getElementById('current-camera');
    const viewModeElement = document.getElementById('view-mode');

    if (currentCameraElement) currentCameraElement.textContent = '듀얼';
    if (viewModeElement) viewModeElement.textContent = '듀얼';

    // 듀얼 모드 API 호출
    fetch('/api/dual_mode/true', { method: 'POST' })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                console.log('[DUAL] 듀얼 모드 API 활성화 성공');
                // 스트림 소스 설정
                document.getElementById('video-stream-0').src = '/stream/0?' + Date.now();
                document.getElementById('video-stream-1').src = '/stream/1?' + Date.now();
            } else {
                console.error('[ERROR] 듀얼 모드 API 실패:', data);
            }
        })
        .catch(error => {
            console.error('[ERROR] 듀얼 모드 초기화 실패:', error);
            // API 실패 시에도 UI는 듀얼 모드로 표시
        });
}

// 듀얼 뷰로 전환
function switchToDualView() {
    console.log('[VIEW] 듀얼 뷰로 전환 클릭');

    // API 호출 중복 방지
    if (isApiCallInProgress) {
        console.log('[VIEW] API 호출 중... 대기');
        return;
    }

    // 즉시 UI 업데이트
    currentViewMode = 'dual';
    currentCamera = null;

    // UI 업데이트
    document.getElementById('dual-view').classList.remove('hidden');
    document.getElementById('single-view').classList.add('hidden');

    // 버튼 활성화 상태 업데이트
    setActiveButton('dual-btn');

    // 상태 텍스트 업데이트 (안전한 접근)
    const currentCameraElement2 = document.getElementById('current-camera');
    const viewModeElement2 = document.getElementById('view-mode');

    if (currentCameraElement2) currentCameraElement2.textContent = '듀얼';
    if (viewModeElement2) viewModeElement2.textContent = '듀얼';

    // 스트림 소스 재설정 (듀얼 모드)
    document.getElementById('video-stream-0').src = '/stream/0?' + Date.now();
    document.getElementById('video-stream-1').src = '/stream/1?' + Date.now();

    // 듀얼 모드 API 호출 (중복 방지)
    isApiCallInProgress = true;
    fetch('/api/dual_mode/true', { method: 'POST' })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                console.log('[DUAL] 듀얼 모드 활성화 성공');
            } else {
                console.error('[ERROR] 듀얼 모드 API 실패:', data);
            }
        })
        .catch(error => console.error('[ERROR] 듀얼 뷰 전환 실패:', error))
        .finally(() => {
            isApiCallInProgress = false;
        });
}

// 싱글 뷰로 전환
function switchToSingleView(cameraId) {
    console.log(`[VIEW] 싱글 뷰로 전환 클릭 - 카메라 ${cameraId}`);

    // 즉시 UI 업데이트
    currentViewMode = 'single';
    currentCamera = cameraId;

    // UI 업데이트
    document.getElementById('dual-view').classList.add('hidden');
    document.getElementById('single-view').classList.remove('hidden');

    // 버튼 활성화 상태 업데이트
    setActiveButton(`cam${cameraId}-btn`);

    // 상태 텍스트 업데이트 (안전한 접근)
    const currentCameraElement3 = document.getElementById('current-camera');
    const viewModeElement3 = document.getElementById('view-mode');
    const singleCameraLabel = document.getElementById('single-camera-label');

    if (currentCameraElement3) currentCameraElement3.textContent = cameraId;
    if (viewModeElement3) viewModeElement3.textContent = `카메라 ${cameraId}`;
    if (singleCameraLabel) singleCameraLabel.textContent = `카메라 ${cameraId}`;

    // 카메라 전환 API 호출 (스트림 업데이트 전에 먼저 실행)
    fetch(`/switch/${cameraId}`, { method: 'POST' })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                console.log(`[VIEW] 카메라 ${cameraId}로 전환 성공`);
                // API 성공 후 스트림 소스 업데이트 (지연 적용)
                setTimeout(() => {
                    document.getElementById('video-stream-single').src = '/stream?' + Date.now();
                    console.log(`[STREAM] 카메라 ${cameraId} 스트림 소스 업데이트`);
                }, 500);
            } else {
                console.error(`[ERROR] 카메라 ${cameraId} 전환 API 실패:`, data);
            }
        })
        .catch(error => console.error(`[ERROR] 카메라 ${cameraId} 전환 실패:`, error));
}

// 버튼 활성화 상태 설정
function setActiveButton(buttonId) {
    // 모든 카메라 버튼 비활성화
    document.querySelectorAll('.camera-btn').forEach(btn => {
        btn.classList.remove('active');
        btn.classList.remove('active-dual');
    });

    // 선택된 버튼 활성화
    const activeBtn = document.getElementById(buttonId);
    if (activeBtn) {
        if (buttonId === 'dual-btn') {
            activeBtn.classList.add('active-dual');
        } else {
            activeBtn.classList.add('active');
        }
    }
}

// 해상도 변경
function changeResolution(resolution) {
    console.log(`[RESOLUTION] ${resolution}로 변경 요청`);

    fetch(`/api/resolution/${resolution}`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log(`[OK] 해상도 변경 완료: ${resolution}`);
                currentResolution = resolution;

                // 해상도 표시 업데이트
                const [width, height] = resolution.split('x');
                document.getElementById('resolution').textContent = `${width}×${height}`;

                // 해상도 버튼 활성화 상태 업데이트
                document.querySelectorAll('.resolution-btn').forEach(btn => {
                    btn.classList.remove('active');
                });

                if (resolution === '640x480') {
                    document.getElementById('res-640-btn').classList.add('active');
                    document.getElementById('dual-view').className = 'dual-view-container resolution-640';
                    document.getElementById('single-view').className = 'single-view-container resolution-640' +
                        (currentViewMode === 'dual' ? ' hidden' : '');
                } else {
                    document.getElementById('res-720-btn').classList.add('active');
                    document.getElementById('dual-view').className = 'dual-view-container resolution-1280';
                    document.getElementById('single-view').className = 'single-view-container resolution-1280' +
                        (currentViewMode === 'dual' ? ' hidden' : '');
                }

                // 스트림 재시작
                setTimeout(() => {
                    if (currentViewMode === 'dual') {
                        document.getElementById('video-stream-0').src = '/stream/0?' + Date.now();
                        document.getElementById('video-stream-1').src = '/stream/1?' + Date.now();
                    } else {
                        document.getElementById('video-stream-single').src = '/stream?' + Date.now();
                    }
                }, 1000);
            }
        })
        .catch(error => {
            console.error('[ERROR] 해상도 변경 실패:', error);
            alert('해상도 변경에 실패했습니다.');
        });
}

// 통계 업데이트
function updateStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            // FPS 업데이트
            document.getElementById('fps').textContent = data.stats.fps || '0.0';

            // 프레임 수 업데이트
            document.getElementById('frame-count').textContent = data.stats.frame_count || '0';

            // 평균 프레임 크기 업데이트
            const avgSize = data.stats.avg_frame_size || 0;
            document.getElementById('frame-size').textContent = `${Math.round(avgSize / 1024)} KB`;

            // 클라이언트 수 업데이트
            const activeClients = data.active_clients || 0;
            const maxClients = data.max_clients || 1;
            document.getElementById('client-count').textContent = `${activeClients}/${maxClients}`;
        })
        .catch(error => {
            console.error('[ERROR] 통계 조회 실패:', error);
        });
}

// 스트림 활성 상태 체크
function checkStreamActivity() {
    console.log('[HEARTBEAT] 상태 체크 시작, 모드:', currentViewMode);

    // 현재 뷰 모드에 따라 적절한 스트림 체크
    const checkUrl = currentViewMode === 'dual' ? '/stream/0' : '/stream';

    fetch(checkUrl, { method: 'HEAD' })
        .then(response => {
            console.log('[HEARTBEAT] 응답 상태:', response.status);

            const indicator = document.getElementById('heartbeat-indicator');
            const text = document.getElementById('heartbeat-text');
            const statusElement = document.getElementById('stream-status');

            if (!indicator || !text || !statusElement) {
                console.error('[HEARTBEAT] HTML 요소를 찾을 수 없음');
                return;
            }

            if (response.status === 200) {
                indicator.className = 'heartbeat-indicator green';
                text.textContent = 'LIVE';
                statusElement.textContent = '연속 녹화 중';
                statusElement.style.color = '#27ae60';
                console.log('[HEARTBEAT] LIVE 상태');
            } else if (response.status === 503) {
                indicator.className = 'heartbeat-indicator black';
                text.textContent = 'OFFLINE';
                statusElement.textContent = '오프라인';
                statusElement.style.color = '#6c757d';
                console.log('[HEARTBEAT] OFFLINE 상태');
            } else if (response.status === 423) {
                indicator.className = 'heartbeat-indicator yellow';
                text.textContent = 'BUSY';
                statusElement.textContent = '접속 제한';
                statusElement.style.color = '#ffc107';
                console.log('[HEARTBEAT] BUSY 상태');
            } else {
                indicator.className = 'heartbeat-indicator yellow';
                text.textContent = 'DELAY';
                statusElement.textContent = '지연';
                statusElement.style.color = '#ffc107';
                console.log('[HEARTBEAT] DELAY 상태:', response.status);
            }
        })
        .catch(error => {
            console.error('[HEARTBEAT] 오류:', error);

            const indicator = document.getElementById('heartbeat-indicator');
            const text = document.getElementById('heartbeat-text');
            const statusElement = document.getElementById('stream-status');

            if (indicator && text && statusElement) {
                indicator.className = 'heartbeat-indicator black';
                text.textContent = 'OFFLINE';
                statusElement.textContent = '서버 연결 끊김';
                statusElement.style.color = '#6c757d';
            }
        });
}

// Recording functionality removed - continuous 30s recording is handled automatically by webmain.py

// ======== AI 감지 관련 함수 ========

// AI 감지 토글
async function toggleAIDetection() {
    if (isApiCallInProgress) return;

    const button = document.getElementById('ai-toggle-btn');
    button.disabled = true;
    isApiCallInProgress = true;

    try {
        const newState = !aiEnabled;
        const response = await fetch(`/api/ai/toggle/${newState}`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            aiEnabled = result.enabled;
            updateAIButton();

            if (aiEnabled) {
                // AI 통계 업데이트 시작
                updateAIStats();
                aiStatsInterval = setInterval(updateAIStats, 2000);
            } else {
                // AI 통계 업데이트 중지
                if (aiStatsInterval) {
                    clearInterval(aiStatsInterval);
                    aiStatsInterval = null;
                }
                // AI 통계 초기화
                document.getElementById('ai-fps').textContent = '0.0';
                document.getElementById('npu-usage').textContent = '0%';
                document.getElementById('total-detections').textContent = '0';
            }

            console.log(`[AI] AI 감지 ${aiEnabled ? '활성화' : '비활성화'}`);
        } else {
            alert('AI 감지 설정 변경에 실패했습니다: ' + result.error);
        }
    } catch (error) {
        console.error('[AI] AI 감지 토글 오류:', error);
        alert('AI 감지 설정 변경 중 오류가 발생했습니다.');
    } finally {
        button.disabled = false;
        isApiCallInProgress = false;
    }
}

// AI 버튼 상태 업데이트
function updateAIButton() {
    const button = document.getElementById('ai-toggle-btn');
    const statusSpan = document.getElementById('ai-status');

    if (aiEnabled) {
        button.textContent = '🤖 AI 감지 비활성화';
        button.classList.add('active');
        statusSpan.textContent = '활성화';
        statusSpan.style.color = '#28a745';
    } else {
        button.textContent = '🤖 AI 감지 활성화';
        button.classList.remove('active');
        statusSpan.textContent = '비활성화';
        statusSpan.style.color = '#6c757d';
    }
}

// AI 통계 업데이트
async function updateAIStats() {
    try {
        const response = await fetch('/api/ai/stats');
        const result = await response.json();

        if (result.success && result.stats.enabled) {
            const stats = result.stats;
            const detectorStats = stats.detector_stats || {};

            // AI 통계 업데이트
            document.getElementById('ai-fps').textContent =
                (detectorStats.inference_fps || 0).toFixed(1);

            // 감지 모드에 따른 처리 방식 표시
            const isHandMode = detectorStats.detection_mode === 'hand';
            const usageValue = isHandMode ?
                (detectorStats.cpu_utilization || 0) :
                (detectorStats.npu_utilization || 0);
            const usageLabel = isHandMode ? 'CPU 사용률' : 'NPU 사용률';

            document.getElementById('npu-usage').textContent = usageValue.toFixed(0) + '%';
            document.getElementById('usage-label').textContent = usageLabel + ':';

            document.getElementById('total-detections').textContent =
                stats.total_detections || 0;

            // 전체 감지 수 업데이트
            const totalDetections = Object.values(stats.camera_detections || {})
                .reduce((sum, count) => sum + count, 0);
            document.getElementById('ai-detections').textContent = totalDetections;
        }
    } catch (error) {
        console.error('[AI] AI 통계 업데이트 오류:', error);
    }
}

// updateStats 함수에 AI 상태 포함
const originalUpdateStats = updateStats;
updateStats = async function() {
    await originalUpdateStats();

    // AI 상태 업데이트
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        if (data.ai_enabled !== undefined) {
            aiEnabled = data.ai_enabled;
            updateAIButton();

            if (data.ai_stats && data.ai_stats.enabled) {
                const totalDetections = Object.values(data.ai_stats.camera_detections || {})
                    .reduce((sum, count) => sum + count, 0);
                document.getElementById('ai-detections').textContent = totalDetections;
            }
        }
    } catch (error) {
        console.error('[AI] AI 상태 업데이트 오류:', error);
    }
};

// 카메라 전환 (레거시 호환성)
function switchCamera(cameraId) {
    switchToSingleView(cameraId);
}

// 페이지 언로드 시 정리
window.addEventListener('beforeunload', function() {
    if (statsInterval) clearInterval(statsInterval);
    if (heartbeatInterval) clearInterval(heartbeatInterval);
    if (aiStatsInterval) clearInterval(aiStatsInterval);
});