#!/bin/bash

# Line Tracer 헤드리스 모드 실행 스크립트 (SSH용)

echo "=========================================="
echo " Line Tracer - Headless Mode"
echo " (SSH Compatible - No Display Required)"
echo "=========================================="
echo ""

# GPIO 그룹 확인
if groups | grep -q gpio; then
    echo "[✓] User has GPIO permissions"
else
    echo "[!] Adding user to GPIO group..."
    sudo usermod -a -G gpio $USER
    echo "    Please logout and login again"
    exit 1
fi

# Python 스크립트 실행
echo "[INFO] Starting Line Tracer in headless mode..."
echo "[INFO] Press Ctrl+C to stop"
echo ""

python3 dual_roi_line_tracer_headless.py

echo ""
echo "[INFO] Line Tracer stopped."
