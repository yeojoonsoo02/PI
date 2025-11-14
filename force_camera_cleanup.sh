#!/bin/bash

echo "=========================================="
echo " 강제 카메라 프로세스 정리"
echo "=========================================="
echo

# 1. 모든 Python 프로세스 강제 종료
echo "1. Python 프로세스 강제 종료..."
sudo pkill -9 python 2>/dev/null
sudo pkill -9 python3 2>/dev/null

# 2. libcamera 관련 프로세스 모두 종료
echo "2. libcamera 프로세스 종료..."
sudo pkill -9 -f libcamera 2>/dev/null
sudo pkill -9 -f picamera 2>/dev/null
sudo pkill -9 -f camera 2>/dev/null

# 3. 특정 파일을 사용하는 프로세스 종료
echo "3. 카메라 디바이스 사용 프로세스 확인..."
sudo fuser -k /dev/video* 2>/dev/null
sudo fuser -k /dev/media* 2>/dev/null

# 4. 2초 대기
echo "4. 2초 대기..."
sleep 2

# 5. 남은 프로세스 확인
echo "5. 프로세스 상태 확인..."
echo
echo "Python 프로세스:"
ps aux | grep python | grep -v grep || echo "  없음"
echo
echo "Camera 프로세스:"
ps aux | grep -E "libcamera|picamera" | grep -v grep || echo "  없음"
echo
echo "카메라 디바이스 사용 프로세스:"
sudo lsof /dev/video* 2>/dev/null || echo "  없음"

echo
echo "=========================================="
echo " ✓ 정리 완료!"
echo "=========================================="
echo
echo "이제 다음 명령을 실행하세요:"
echo "python /home/keonha/AI_CAR/new.py"