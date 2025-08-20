#!/bin/bash

# FabCam CCTV System - 통합 실행 스크립트
# 자동으로 환경을 감지하고 설정합니다.

set -e  # 오류 발생시 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로고 출력
echo -e "${BLUE}"
echo "╔════════════════════════════════════════╗"
echo "║        🎥 FabCam CCTV System 🎥        ║"
echo "║     Raspberry Pi Camera Solution       ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

# PATH에 uv 추가
export PATH="$HOME/.local/bin:$PATH"

# 1. uv 설치 확인
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}📦 uv가 없습니다. 설치를 진행합니다...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo -e "${GREEN}✅ uv 설치 완료${NC}"
else
    echo -e "${GREEN}✅ uv 확인됨: $(uv --version)${NC}"
fi

# 2. 가상환경 확인 및 생성
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}🐍 Python 가상환경 생성 중...${NC}"
    uv venv --python 3.11
    echo -e "${GREEN}✅ 가상환경 생성 완료${NC}"
fi

# 3. 가상환경 활성화
echo -e "${BLUE}🔧 가상환경 활성화 중...${NC}"
source .venv/bin/activate

# 4. 의존성 확인 및 설치
echo -e "${BLUE}⚡ 의존성 확인 중...${NC}"
if ! python -c "import fastapi, uvicorn, cv2" 2>/dev/null; then
    echo -e "${YELLOW}📦 의존성 설치 중 (빠른 uv 사용)...${NC}"
    uv pip install -e . 2>/dev/null || \
    uv pip install fastapi uvicorn[standard] opencv-python python-multipart jinja2 aiofiles
    echo -e "${GREEN}✅ 의존성 설치 완료${NC}"
else
    echo -e "${GREEN}✅ 모든 의존성이 이미 설치됨${NC}"
fi

# 5. 디렉토리 구조 확인
echo -e "${BLUE}📁 디렉토리 확인 중...${NC}"
mkdir -p static/videos static/images
echo -e "${GREEN}✅ 디렉토리 준비 완료${NC}"

# 6. 카메라 감지
echo -e "${BLUE}📷 카메라 감지 중...${NC}"
if command -v rpicam-hello &> /dev/null; then
    if rpicam-hello --list-cameras 2>/dev/null | grep -q "Available cameras"; then
        echo -e "${GREEN}✅ Raspberry Pi 카메라 감지됨${NC}"
        MAIN_SCRIPT="main_auto.py"
    else
        echo -e "${YELLOW}⚠️ Pi 카메라 없음, USB 카메라 모드${NC}"
        MAIN_SCRIPT="main.py"
    fi
else
    echo -e "${YELLOW}⚠️ rpicam 도구 없음, OpenCV 모드${NC}"
    MAIN_SCRIPT="main.py"
fi

# 7. 서버 시작
echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}🌐 서버 시작 중...${NC}"
echo -e "${BLUE}📍 로컬 접속: http://localhost:8000${NC}"
echo -e "${BLUE}📍 네트워크 접속: http://$(hostname -I | awk '{print $1}'):8000${NC}"
echo -e "${YELLOW}🛑 종료: Ctrl+C${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""

cd backend
python $MAIN_SCRIPT