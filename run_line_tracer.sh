#!/bin/bash

# 카메라 프로세스 정리 및 라인 트레이서 실행
echo "카메라 정리 중..."

# Python 프로세스 종료
sudo pkill -9 python 2>/dev/null
sudo pkill -9 python3 2>/dev/null

# libcamera 프로세스 종료
sudo pkill -9 -f libcamera 2>/dev/null

# 2초 대기
sleep 2

# 프로그램 실행
echo "라인 트레이서 시작..."
python /home/keonha/AI_CAR/new.py