#!/bin/bash

echo "========================================"
echo " YOLO 모델 파일 설정 스크립트"
echo "========================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 가능한 모델 파일 위치들
MODEL_LOCATIONS=(
    "/home/keonha/AI_CAR/best.pt"
    "/home/keonha/AI_CAR/test/best.pt"
    "/home/keonha/AI_CAR/product/best.pt"
    "/home/keonha/best.pt"
    "/home/pi/AI_CAR/best.pt"
    "/home/pi/best.pt"
    "$(pwd)/best.pt"
)

echo -e "\n${YELLOW}[1] 현재 best.pt 파일 찾기...${NC}"
FOUND=false
EXISTING_MODEL=""

for loc in "${MODEL_LOCATIONS[@]}"; do
    if [ -f "$loc" ]; then
        echo -e "${GREEN}  ✓ 발견: $loc${NC}"
        EXISTING_MODEL="$loc"
        FOUND=true
        break
    fi
done

if [ "$FOUND" = false ]; then
    echo -e "${RED}  ✗ best.pt 파일을 찾을 수 없습니다!${NC}"
    echo ""
    echo -e "${YELLOW}[해결 방법]${NC}"
    echo "1. 로컬에서 라즈베리파이로 모델 파일 전송:"
    echo "   scp /path/to/best.pt keonha@raspberrypi:/home/keonha/AI_CAR/"
    echo ""
    echo "2. 또는 USB로 복사 후:"
    echo "   cp /media/usb/best.pt /home/keonha/AI_CAR/"
    exit 1
fi

echo -e "\n${YELLOW}[2] test 디렉토리에 모델 파일 복사...${NC}"

# test 디렉토리가 있는지 확인
if [ -d "/home/keonha/AI_CAR/test" ]; then
    if [ ! -f "/home/keonha/AI_CAR/test/best.pt" ]; then
        cp "$EXISTING_MODEL" "/home/keonha/AI_CAR/test/best.pt"
        echo -e "${GREEN}  ✓ /home/keonha/AI_CAR/test/best.pt 생성됨${NC}"
    else
        echo -e "${GREEN}  ✓ /home/keonha/AI_CAR/test/best.pt 이미 존재${NC}"
    fi
fi

# product 디렉토리가 있는지 확인
if [ -d "/home/keonha/AI_CAR/product" ]; then
    if [ ! -f "/home/keonha/AI_CAR/product/best.pt" ]; then
        cp "$EXISTING_MODEL" "/home/keonha/AI_CAR/product/best.pt"
        echo -e "${GREEN}  ✓ /home/keonha/AI_CAR/product/best.pt 생성됨${NC}"
    else
        echo -e "${GREEN}  ✓ /home/keonha/AI_CAR/product/best.pt 이미 존재${NC}"
    fi
fi

# 메인 디렉토리에도 복사
if [ ! -f "/home/keonha/AI_CAR/best.pt" ]; then
    cp "$EXISTING_MODEL" "/home/keonha/AI_CAR/best.pt"
    echo -e "${GREEN}  ✓ /home/keonha/AI_CAR/best.pt 생성됨${NC}"
else
    echo -e "${GREEN}  ✓ /home/keonha/AI_CAR/best.pt 이미 존재${NC}"
fi

echo -e "\n${YELLOW}[3] 파일 권한 설정...${NC}"
chmod 644 /home/keonha/AI_CAR/best.pt 2>/dev/null
chmod 644 /home/keonha/AI_CAR/test/best.pt 2>/dev/null
chmod 644 /home/keonha/AI_CAR/product/best.pt 2>/dev/null
echo -e "${GREEN}  ✓ 권한 설정 완료${NC}"

echo -e "\n${YELLOW}[4] 설정 완료 확인${NC}"
echo -e "${GREEN}다음 위치에 모델 파일이 있습니다:${NC}"
ls -lh /home/keonha/AI_CAR/best.pt 2>/dev/null && echo "  • /home/keonha/AI_CAR/best.pt"
ls -lh /home/keonha/AI_CAR/test/best.pt 2>/dev/null && echo "  • /home/keonha/AI_CAR/test/best.pt"
ls -lh /home/keonha/AI_CAR/product/best.pt 2>/dev/null && echo "  • /home/keonha/AI_CAR/product/best.pt"

echo -e "\n${GREEN}========================================"
echo " 설정 완료! 이제 프로그램을 실행하세요:"
echo "========================================"
echo ""
echo " cd /home/keonha/AI_CAR/test"
echo " python3 main.py"
echo ""
echo "========================================"${NC}