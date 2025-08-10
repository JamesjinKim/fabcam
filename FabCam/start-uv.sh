#!/bin/bash

echo "🚀 Fabcam CCTV System (UV 버전) 시작 중..."

# PATH에 uv 추가
export PATH="$HOME/.local/bin:$PATH"

# 가상환경 존재 확인
if [ ! -d ".venv" ]; then
    echo "❌ 가상환경이 없습니다. 먼저 ./setup-uv.sh를 실행하세요."
    echo "   또는 다음 명령을 실행하세요: ./setup-uv.sh"
    exit 1
fi

echo "🐍 가상환경 활성화 중..."
source .venv/bin/activate

# 의존성 빠른 확인 (필요시에만 설치)
echo "⚡ 의존성 확인 중..."
if ! python -c "import fastapi, uvicorn, cv2" 2>/dev/null; then
    echo "📦 누락된 의존성을 빠르게 설치 중..."
    uv pip install fastapi uvicorn[standard] opencv-python python-multipart jinja2 aiofiles
fi

# 저장 디렉토리 확인
echo "📁 디렉토리 확인 중..."
mkdir -p static/videos static/images

# 서버 시작
echo ""
echo "🌐 서버 시작 중..."
echo "📍 접속 주소: http://localhost:8000"
echo "🔧 종료하려면 Ctrl+C를 누르세요"
echo "⚡ UV로 구동되는 고속 환경!"
echo ""

cd backend
python main.py