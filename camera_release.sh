#!/bin/bash

# 카메라 관련 프로세스 종료 스크립트
echo "========================================"
echo " 카메라 프로세스 정리 중..."
echo "========================================"

# 카메라를 사용 중인 Python 프로세스 찾기
echo "1. Python 카메라 프로세스 확인..."
ps aux | grep -E "python.*camera|python.*line|python.*tracer" | grep -v grep

# 카메라 관련 프로세스 종료
echo ""
echo "2. 카메라 프로세스 종료 중..."

# picamera2 관련 프로세스 종료
pkill -f "python.*camera" 2>/dev/null
pkill -f "python.*line" 2>/dev/null
pkill -f "python.*tracer" 2>/dev/null
pkill -f "picamera2" 2>/dev/null

# libcamera 관련 프로세스 종료
pkill -f "libcamera" 2>/dev/null

sleep 1

echo ""
echo "3. 남은 프로세스 확인..."
remaining=$(ps aux | grep -E "python.*camera|python.*line|python.*tracer|libcamera" | grep -v grep | wc -l)

if [ $remaining -eq 0 ]; then
    echo "✓ 모든 카메라 프로세스가 종료되었습니다."
else
    echo "⚠ 아직 실행 중인 프로세스가 있습니다:"
    ps aux | grep -E "python.*camera|python.*line|python.*tracer|libcamera" | grep -v grep
    echo ""
    echo "강제 종료하려면 다음 명령을 사용하세요:"
    echo "sudo pkill -9 -f python"
fi

echo ""
echo "========================================"
echo " 완료! 이제 프로그램을 다시 실행하세요."
echo "========================================"