#!/bin/bash
# fabcam.sh - SHT 듀얼 LIVE AI 카메라 통합 관리 스크립트
# Raspberry Pi 5 + Hailo AI Kit + Dual Camera CCTV System
#
# 사용법: ./fabcam.sh [명령]
# 명령어: install, install-hailo, install-driver, setup, run, status, help

set -e  # 오류 발생 시 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 전역 변수
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_NAME="venv_fabcam"
CONFIG_FILE="config.json"
LOG_FILE="fabcam_install.log"

# ============================================================================
# 공통 함수
# ============================================================================

print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        return 1
    fi
    return 0
}

check_file_exists() {
    if [ ! -f "$1" ]; then
        print_error "파일을 찾을 수 없습니다: $1"
        return 1
    fi
    return 0
}

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

check_package_installed() {
    if dpkg -l | grep -q "^ii  $1 "; then
        return 0
    fi
    return 1
}

# ============================================================================
# Hailo 관련 함수
# ============================================================================

check_hailo_hardware() {
    if lspci 2>/dev/null | grep -q "Hailo"; then
        print_success "Hailo NPU 하드웨어 감지됨"
        return 0
    else
        print_info "Hailo NPU 하드웨어 미감지"
        return 1
    fi
}

check_hailo_device() {
    if [ -c "/dev/hailo0" ]; then
        print_success "Hailo 디바이스 파일 확인됨"
        return 0
    else
        print_warning "Hailo 디바이스 파일 없음"
        return 1
    fi
}

check_hailo_driver() {
    if lsmod | grep -q "hailo"; then
        print_success "Hailo 드라이버 로드됨"
        return 0
    else
        print_warning "Hailo 드라이버 미로드"
        return 1
    fi
}

install_hailo_full() {
    print_header "Hailo AI Kit 전체 설치"

    # 1. 시스템 업데이트
    print_info "[1/6] 시스템 패키지 업데이트..."
    sudo apt update
    sudo apt upgrade -y

    # 2. 필수 의존성 설치
    print_info "[2/6] 필수 패키지 설치..."
    sudo apt install -y \
        build-essential \
        cmake \
        git \
        wget \
        python3-dev \
        python3-pip \
        python3-venv \
        libopencv-dev \
        python3-opencv \
        libgirepository1.0-dev \
        gcc-12 \
        g++-12

    # 3. Hailo 저장소 추가
    print_info "[3/6] Hailo 공식 저장소 추가..."
    if [ ! -f /etc/apt/sources.list.d/hailo.list ]; then
        wget -qO - https://hailo.ai/wp-content/uploads/2023/08/hailo.gpg | sudo apt-key add -
        echo "deb https://hailo.ai/raspbian/ bookworm main" | sudo tee /etc/apt/sources.list.d/hailo.list
        sudo apt update
    fi

    # 4. HailoRT 및 드라이버 설치
    print_info "[4/6] HailoRT 설치..."
    sudo apt install -y hailort hailort-pcie-driver

    # 5. Python 바인딩 설치
    print_info "[5/6] Python 바인딩 설치..."
    pip3 install --upgrade pip
    pip3 install hailort

    # 6. 펌웨어 업데이트 확인
    print_info "[6/6] Hailo 장치 확인..."
    sudo modprobe hailo_pcie || true
    sudo hailortcli fw-control identify || true

    print_success "Hailo AI Kit 설치 완료!"
}

install_hailo_driver_only() {
    print_header "Hailo PCIe 드라이버 설치"

    print_info "Kernel: $(uname -r)"

    # 1. 필수 패키지 설치
    print_info "[1/5] 필수 빌드 도구 설치..."
    sudo apt update
    sudo apt install -y \
        raspberrypi-kernel-headers \
        dkms \
        build-essential \
        git \
        cmake

    # 2. 드라이버 소스 다운로드
    print_info "[2/5] Hailo PCIe 드라이버 다운로드..."
    cd /tmp
    if [ -d "hailort-drivers" ]; then
        rm -rf hailort-drivers
    fi
    git clone https://github.com/hailo-ai/hailort-drivers.git
    cd hailort-drivers

    # 3. 드라이버 빌드
    print_info "[3/5] 드라이버 빌드..."
    cd linux/pcie
    make clean
    make

    # 4. 드라이버 설치
    print_info "[4/5] 드라이버 설치..."
    sudo make install
    sudo depmod -a

    # 5. 드라이버 로드
    print_info "[5/5] 드라이버 로드..."
    sudo modprobe hailo_pcie

    # 원래 디렉토리로 복귀
    cd "$SCRIPT_DIR"

    print_success "드라이버 설치 완료!"
    check_hailo_driver
}

# ============================================================================
# Python 환경 관련 함수
# ============================================================================

setup_python_environment() {
    print_header "Python 환경 설정"

    # 1. 가상환경 생성
    print_info "1. 가상환경 생성 중..."
    if [ ! -d "$VENV_NAME" ]; then
        python3 -m venv "$VENV_NAME" --system-site-packages
        print_success "가상환경 생성 완료"
    else
        print_info "가상환경이 이미 존재합니다."
    fi

    # 2. 가상환경 활성화 및 의존성 설치
    print_info "2. Python 패키지 설치 중..."
    source "$VENV_NAME/bin/activate"

    # requirements.txt가 있으면 사용, 없으면 직접 설치
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        pip install --upgrade pip
        pip install fastapi uvicorn opencv-python numpy psutil
    fi
    print_success "Python 패키지 설치 완료"

    # 3. 시스템 패키지 확인
    print_info "3. 시스템 패키지 확인 중..."
    local missing_packages=()

    for pkg in python3-picamera2 python3-libcamera ffmpeg; do
        if ! check_package_installed "$pkg"; then
            missing_packages+=("$pkg")
            print_error "$pkg 미설치"
        else
            print_success "$pkg 설치됨"
        fi
    done

    if [ ${#missing_packages[@]} -gt 0 ]; then
        print_warning "다음 시스템 패키지가 필요합니다:"
        for pkg in "${missing_packages[@]}"; do
            echo "   - $pkg"
        done
        echo ""
        echo "다음 명령어로 설치하세요:"
        echo "sudo apt update && sudo apt install -y ${missing_packages[*]}"
        echo ""
    fi

    # 4. 모듈 테스트
    print_info "4. 환경 테스트 중..."
    python3 -c "
import sys
try:
    import fastapi
    import uvicorn
    print('✅ 필수 모듈 임포트 성공!')
except ImportError as e:
    print(f'❌ 모듈 오류: {e}')
    sys.exit(1)
"

    print_success "Python 환경 설정 완료!"
}

# ============================================================================
# 실행 관련 함수
# ============================================================================

run_fabcam() {
    print_header "SHT 듀얼 LIVE 카메라 + Hailo AI 시스템 시작"

    # webmain.py 확인
    if [ ! -f "webmain.py" ]; then
        print_error "webmain.py 파일을 찾을 수 없습니다."
        exit 1
    fi

    # 가상환경 확인
    if [ ! -d "$VENV_NAME" ]; then
        print_error "가상환경이 설정되지 않았습니다."
        echo "다음 명령어로 환경을 설정하세요: $0 setup"
        exit 1
    fi

    # 가상환경 활성화
    print_info "가상환경 활성화 중..."
    source "$VENV_NAME/bin/activate"

    # 모듈 확인
    print_info "필수 모듈 확인 중..."
    python3 -c "
try:
    import fastapi
    import uvicorn
    from web.api import CCTVWebAPI
    print('✅ 모든 모듈 확인 완료')
except ImportError as e:
    print(f'❌ 모듈 오류: {e}')
    print('환경 설정을 다시 실행하세요: $0 setup')
    exit(1)
"

    if [ $? -ne 0 ]; then
        exit 1
    fi

    # 시스템 정보 표시
    echo ""
    print_info "시스템 정보:"
    echo "   - 가상환경: $(python3 -c 'import sys; print(sys.prefix)')"
    echo "   - Python: $(python3 --version)"
    echo "   - 현재 디렉토리: $(pwd)"
    echo ""

    # 웹 서버 시작
    local ip_addr=$(hostname -I | awk '{print $1}')
    print_success "웹 서버 시작 중..."
    echo "   접속 주소: http://${ip_addr}:8001"
    echo ""
    print_warning "종료하려면 Ctrl+C를 누르세요"
    echo ""

    # webmain.py 실행
    python3 webmain.py
}

# ============================================================================
# 상태 확인 함수
# ============================================================================

check_system_status() {
    print_header "시스템 상태 확인"

    echo -e "\n${BLUE}[기본 시스템]${NC}"
    echo -n "  • Python: "
    if check_command python3; then
        print_success "$(python3 --version)"
    else
        print_error "미설치"
    fi

    echo -n "  • 가상환경: "
    if [ -d "$VENV_NAME" ]; then
        print_success "설정됨 ($VENV_NAME)"
    else
        print_error "미설정"
    fi

    echo -n "  • webmain.py: "
    if [ -f "webmain.py" ]; then
        print_success "존재함"
    else
        print_error "없음"
    fi

    echo -n "  • config.json: "
    if [ -f "$CONFIG_FILE" ]; then
        print_success "존재함"
    else
        print_warning "없음 (기본값 사용)"
    fi

    echo -e "\n${BLUE}[카메라 시스템]${NC}"
    echo -n "  • picamera2: "
    if check_package_installed python3-picamera2; then
        print_success "설치됨"
    else
        print_error "미설치"
    fi

    echo -n "  • libcamera: "
    if check_package_installed python3-libcamera; then
        print_success "설치됨"
    else
        print_error "미설치"
    fi

    echo -n "  • ffmpeg: "
    if check_command ffmpeg; then
        print_success "설치됨"
    else
        print_error "미설치"
    fi

    echo -e "\n${BLUE}[Hailo AI Kit]${NC}"
    echo -n "  • NPU 하드웨어: "
    if check_hailo_hardware; then
        :
    else
        :
    fi

    echo -n "  • 드라이버: "
    if check_hailo_driver; then
        :
    else
        :
    fi

    echo -n "  • 디바이스 파일: "
    if check_hailo_device; then
        :
    else
        :
    fi

    echo -n "  • HailoRT: "
    if check_command hailortcli; then
        print_success "설치됨"
    else
        print_warning "미설치"
    fi

    echo -e "\n${BLUE}[웹 서버]${NC}"
    echo -n "  • FastAPI: "
    if [ -d "$VENV_NAME" ]; then
        source "$VENV_NAME/bin/activate" 2>/dev/null
        if python3 -c "import fastapi" 2>/dev/null; then
            print_success "설치됨"
        else
            print_error "미설치"
        fi
    else
        print_warning "가상환경 미설정"
    fi

    echo -n "  • 포트 8001: "
    if netstat -tuln 2>/dev/null | grep -q ":8001 "; then
        print_warning "사용 중 (서버 실행 중)"
    else
        print_success "사용 가능"
    fi

    echo ""
}

# ============================================================================
# 전체 설치 함수
# ============================================================================

install_all() {
    print_header "전체 시스템 설치"
    log_message "전체 설치 시작"

    # 1. Hailo 설치
    if check_hailo_hardware && check_hailo_driver; then
        print_info "Hailo가 이미 설치되어 있습니다. 건너뜁니다."
    else
        install_hailo_full
    fi

    # 2. Python 환경 설정
    setup_python_environment

    # 3. 디렉토리 생성
    print_info "필수 디렉토리 생성 중..."
    mkdir -p videos/cam0 videos/cam1
    mkdir -p snapshots/detections snapshots/alerts
    mkdir -p models

    print_success "전체 설치 완료!"
    log_message "전체 설치 완료"

    echo ""
    print_info "시작 명령어: $0 run"
}

# ============================================================================
# 도움말 함수
# ============================================================================

show_help() {
    cat << EOF
${BLUE}fabcam.sh - SHT 듀얼 LIVE AI 카메라 통합 관리 스크립트${NC}

${YELLOW}사용법:${NC}
  $0 [명령]

${YELLOW}명령어:${NC}
  ${GREEN}install${NC}        전체 시스템 설치 (Hailo + Python 환경)
  ${GREEN}install-hailo${NC}  Hailo AI Kit 전체 설치
  ${GREEN}install-driver${NC} Hailo PCIe 드라이버만 설치
  ${GREEN}setup${NC}          Python 환경만 설정
  ${GREEN}run${NC}            시스템 실행
  ${GREEN}status${NC}         시스템 상태 확인
  ${GREEN}help${NC}           이 도움말 표시

${YELLOW}예제:${NC}
  처음 설치:     $0 install
  서버 실행:     $0 run
  상태 확인:     $0 status

${YELLOW}웹 인터페이스:${NC}
  http://라즈베리파이IP:8001

${YELLOW}문제 해결:${NC}
  Hailo 미감지:  sudo modprobe hailo_pcie
  권한 오류:     sudo 사용 필요한 명령어 확인

EOF
}

# ============================================================================
# 메인 처리
# ============================================================================

main() {
    cd "$SCRIPT_DIR"

    case "${1:-help}" in
        install)
            install_all
            ;;
        install-hailo)
            if check_root; then
                install_hailo_full
            else
                print_error "이 명령어는 root 권한이 필요합니다. sudo를 사용하세요."
                exit 1
            fi
            ;;
        install-driver)
            if check_root; then
                install_hailo_driver_only
            else
                print_error "이 명령어는 root 권한이 필요합니다. sudo를 사용하세요."
                exit 1
            fi
            ;;
        setup)
            setup_python_environment
            ;;
        run|start)
            run_fabcam
            ;;
        status)
            check_system_status
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "알 수 없는 명령어: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"