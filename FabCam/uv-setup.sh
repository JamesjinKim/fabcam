#!/bin/bash

echo "🚀 Fabcam CCTV System - UV 설정 시작..."

# uv 설치 확인
if ! command -v uv &> /dev/null; then
    echo "📦 uv 설치 중..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
    export PATH="$HOME/.cargo/bin:$PATH"
fi

echo "✅ uv 버전: $(uv --version)"

# 프로젝트 초기화 (기존 파일들 유지하며)
echo "🔧 프로젝트 환경 설정 중..."

# 가상환경 생성 및 활성화
echo "🐍 Python 가상환경 생성 중..."
uv venv --python 3.11

# 의존성 설치
echo "📦 의존성 설치 중..."
uv pip install -e .

# 개발 의존성 설치 (선택사항)
echo "🛠️  개발 의존성 설치 중..."
uv pip install -e ".[dev]"

# 저장 디렉토리 생성
echo "📁 디렉토리 구조 생성 중..."
mkdir -p static/videos static/images

echo "✅ UV 설정 완료!"
echo ""
echo "🎯 사용법:"
echo "  1. 가상환경 활성화: source .venv/bin/activate"
echo "  2. 서버 시작: cd backend && python main.py"
echo "  3. 또는 간단하게: ./start-uv.sh"
echo ""
echo "🔧 UV 명령어:"
echo "  - uv pip install <package>  # 패키지 설치"
echo "  - uv pip list              # 설치된 패키지 목록"
echo "  - uv sync                  # 의존성 동기화"