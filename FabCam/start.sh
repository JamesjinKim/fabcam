#!/bin/bash

echo "🚀 Fabcam CCTV System 시작 중..."

# 가상환경 활성화 (있는 경우)
if [ -d "venv" ]; then
    echo "📦 가상환경 활성화 중..."
    source venv/bin/activate
fi

# 의존성 설치 확인
echo "📋 의존성 확인 중..."
pip install -r requirements.txt

# 저장 디렉토리 생성
echo "📁 디렉토리 생성 중..."
mkdir -p static/videos
mkdir -p static/images

# 서버 시작
echo "🌐 서버 시작 중..."
cd backend
python main.py