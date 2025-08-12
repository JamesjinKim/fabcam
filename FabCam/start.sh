#!/bin/bash

echo "🚀 Fabcam CCTV System 시작 중..."

# 시스템 Python 사용 (라즈베리파이 권장)
echo "📋 시스템 패키지 사용 (FastAPI, OpenCV 설치됨)..."

# 저장 디렉토리 생성
echo "📁 디렉토리 생성 중..."
mkdir -p static/videos
mkdir -p static/images

# 서버 시작
echo "🌐 서버 시작 중..."
cd backend
/usr/bin/python3 main.py