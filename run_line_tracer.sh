#!/bin/bash

# Line Tracer 실행 스크립트
# 라즈베리파이에서 실행 시 카메라 권한 문제 해결

echo "=========================================="
echo " Line Tracer with Junction Detection"
echo "=========================================="
echo ""

# 카메라 디바이스 확인
if [ -e /dev/video0 ]; then
    echo "[✓] Camera device found: /dev/video0"
else
    echo "[✗] Camera device not found!"
    echo "    Please check camera connection."
    exit 1
fi

# 카메라 권한 확인
if [ ! -r /dev/video0 ]; then
    echo "[!] Camera permission issue. Adding user to video group..."
    sudo usermod -a -G video $USER
    echo "    Please logout and login again for changes to take effect."
    exit 1
fi

# Python 스크립트 실행
echo "[INFO] Starting Line Tracer..."
echo ""

python3 dual_roi_line_tracer_improved.py

echo ""
echo "[INFO] Line Tracer stopped."
