#!/bin/bash

echo "=========================================="
echo " 카메라 프로세스 정리 중..."
echo "=========================================="
echo

# 실행 중인 Python 프로세스 확인
echo "1. Python 프로세스 확인..."
ps aux | grep python | grep -v grep

# Python 프로세스 종료
echo
echo "2. Python 프로세스 종료..."
pkill -f "python.*new\.py" 2>/dev/null
pkill -f "python.*line_tracer" 2>/dev/null
pkill -f python3 2>/dev/null

# libcamera 프로세스 종료
echo
echo "3. libcamera 프로세스 종료..."
pkill -f libcamera 2>/dev/null

# 1초 대기
sleep 1

# 남은 프로세스 확인
echo
echo "4. 남은 카메라 프로세스 확인..."
remaining=$(ps aux | grep -E "python|libcamera" | grep -v grep | wc -l)

if [ $remaining -eq 0 ]; then
    echo "✓ 모든 카메라 프로세스가 종료되었습니다."
else
    echo "⚠ 아직 실행 중인 프로세스가 있습니다:"
    ps aux | grep -E "python|libcamera" | grep -v grep
fi

echo
echo "=========================================="
echo " 완료! 이제 프로그램을 실행할 수 있습니다."
echo "=========================================="
echo
echo "실행 명령:"
echo "python /home/keonha/AI_CAR/new.py"