#!/bin/bash

echo "🚀 Fabcam CCTV System - UV 환경 설정 시작..."

# PATH에 uv 추가
export PATH="$HOME/.local/bin:$PATH"

# uv 설치 확인
if ! command -v uv &> /dev/null; then
    echo "❌ uv가 설치되지 않았습니다. 설치를 진행합니다..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "✅ uv 버전: $(uv --version)"

# 가상환경이 없으면 생성
if [ ! -d ".venv" ]; then
    echo "🐍 Python 가상환경 생성 중..."
    uv venv --python 3.11
fi

# 가상환경 활성화
echo "🔧 가상환경 활성화 중..."
source .venv/bin/activate

# 의존성 설치 (매우 빠름!)
echo "⚡ 의존성 설치 중 (uv 사용)..."
uv pip install fastapi uvicorn[standard] opencv-python python-multipart jinja2 aiofiles

# 저장 디렉토리 생성
echo "📁 디렉토리 구조 생성 중..."
mkdir -p static/videos static/images

echo "✅ UV 환경 설정 완료!"
echo ""
echo "🎯 사용법:"
echo "  1. 서버 시작: ./start-uv.sh"
echo "  2. 또는 수동으로:"
echo "     - source .venv/bin/activate"
echo "     - cd backend && python main.py"
echo ""
echo "⚡ UV의 장점을 확인해보세요:"
echo "  - 설치 속도: pip 대비 10-20배 빠름"
echo "  - 의존성 해결: PubGrub 알고리즘으로 빠른 충돌 해결"
echo "  - 재현가능성: 정확한 버전 관리"