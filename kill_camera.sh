#!/bin/bash
# 카메라 프로세스 강제 종료 스크립트

echo "카메라 프로세스 종료 중..."

# 모든 Python 프로세스 종료
sudo pkill -9 python
sudo pkill -9 python3

# libcamera 관련 프로세스 종료
sudo pkill -9 -f libcamera
sudo pkill -9 -f picamera
sudo pkill -9 -f camera

# 1초 대기
sleep 1

echo "✓ 완료! 이제 프로그램을 실행하세요."
echo "python /home/keonha/AI_CAR/new.py"