#!/bin/bash

# Simple Line Follower 실행 스크립트

echo "==========================================="
echo " Simple Yellow Line Follower"
echo " - No junction detection"
echo " - Pure line following"
echo "==========================================="
echo ""

# GPIO 권한 확인
if groups | grep -q gpio; then
    echo "[✓] GPIO permissions OK"
else
    echo "[!] Adding user to GPIO group..."
    sudo usermod -a -G gpio $USER
    echo "    Please logout and login again"
    exit 1
fi

# 실행
echo "[INFO] Starting simple line follower..."
echo "[INFO] Press Ctrl+C to stop"
echo ""

python3 simple_line_follower.py

echo ""
echo "[INFO] Stopped."
