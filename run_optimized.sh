#!/bin/bash

# Optimized Line Tracer 실행 스크립트

echo "=========================================="
echo " Optimized Yellow Line Tracer"
echo " - Clean code architecture"
echo " - Auto parameter tuning"
echo " - Real-time statistics"
echo "=========================================="
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
echo "[INFO] Starting optimized line tracer..."
echo "[INFO] Press Ctrl+C to stop"
echo ""

python3 line_tracer_optimized.py

echo ""
echo "[INFO] Stopped."
