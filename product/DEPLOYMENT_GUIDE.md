# 라즈베리파이 배포 가이드
## 📅 2024-11-13

## 🚀 빠른 시작 가이드

### 1. **모델 파일 배포**

#### 로컬 컴퓨터에서 라즈베리파이로 모델 파일 복사
```bash
# Mac/Linux에서 실행 (best.pt 파일 전송)
scp /Users/yeojoonsoo02/Desktop/Python_Project/PI/best.pt keonha@[라즈베리파이IP]:/home/keonha/AI_CAR/

# 또는 product 디렉토리로 복사
scp /Users/yeojoonsoo02/Desktop/Python_Project/PI/best.pt keonha@[라즈베리파이IP]:/home/keonha/AI_CAR/product/
```

### 2. **카메라 오류 해결**

#### 카메라 프로세스 확인 및 종료
```bash
# 카메라를 사용하는 프로세스 찾기
sudo fuser -v /dev/video0

# 카메라 사용 프로세스 강제 종료
sudo fuser -k /dev/video0

# 또는 libcamera 프로세스 종료
sudo pkill libcamera
sudo pkill raspivid
sudo pkill raspistill

# Python 프로세스 종료 (필요시)
sudo pkill -f python3
```

### 3. **프로그램 실행**

#### 코드 파일 전송 (필요시)
```bash
# 전체 product 디렉토리 전송
scp -r /Users/yeojoonsoo02/Desktop/Python_Project/PI/product keonha@[라즈베리파이IP]:/home/keonha/AI_CAR/
```

#### 라즈베리파이에서 실행
```bash
# SSH 접속
ssh keonha@[라즈베리파이IP]

# 프로젝트 디렉토리로 이동
cd /home/keonha/AI_CAR/product

# 실행 권한 부여
chmod +x *.py

# 프로그램 실행
sudo python3 main.py
```

## 🔧 문제 해결

### 카메라 오류: "Pipeline handler in use"
```bash
# 해결 방법 1: 모든 카메라 프로세스 종료
sudo pkill -f camera
sudo pkill -f video
sudo systemctl restart camera  # 카메라 서비스 재시작 (있는 경우)

# 해결 방법 2: 재부팅
sudo reboot
```

### 모델 파일을 찾을 수 없음
```bash
# 모델 파일 위치 확인
ls -la /home/keonha/AI_CAR/*.pt
ls -la /home/keonha/AI_CAR/product/*.pt

# 모델 파일이 없으면 다시 복사
# 로컬 컴퓨터에서:
scp /Users/yeojoonsoo02/Desktop/Python_Project/PI/best.pt keonha@[라즈베리파이IP]:/home/keonha/AI_CAR/
```

### GPIO 권한 오류
```bash
# GPIO 그룹에 사용자 추가
sudo usermod -a -G gpio $USER
sudo usermod -a -G video $USER

# 로그아웃 후 다시 로그인 또는
sudo su - $USER
```

## 📋 체크리스트

### 실행 전 확인사항
- [ ] best.pt 모델 파일이 라즈베리파이에 있는가?
- [ ] 카메라가 연결되어 있는가?
- [ ] 다른 프로세스가 카메라를 사용하고 있지 않은가?
- [ ] GPIO 핀이 올바르게 연결되어 있는가?
- [ ] Python 패키지가 모두 설치되어 있는가?

### 필요한 Python 패키지
```bash
pip3 install opencv-python
pip3 install ultralytics
pip3 install gpiozero
pip3 install numpy
```

## 🎯 표지판 인식 동작 원리

### 시스템 구조
1. **카메라 프레임 공유**: lane_tracer.py가 3프레임마다 object_detector.py와 프레임 공유
2. **객체 감지**: YOLO 모델이 표지판 감지 (오른쪽 절반 ROI만 스캔)
3. **큐에 저장**: 감지된 표지판을 큐에 저장 (최대 5개)
4. **교차로에서 실행**: 교차로 감지 시 저장된 표지판 명령 실행

### 지원되는 표지판
- **go_straight**: 직진
- **turn_left**: 좌회전
- **turn_right**: 우회전
- **stop**: 정지
- **slow**: 서행
- **horn**: 경적
- **traffic**: 신호등

### 디버그 로그 확인
프로그램 실행 시 다음과 같은 로그가 표시되어야 합니다:
```
======================================================================
 YOLOv8 Object Detector (BGR→RGB 변환 적용)
======================================================================
  [INFO] YOLO 모델 파일 검색 중...
  [✓] 모델 파일 발견: /home/keonha/AI_CAR/best.pt
  [✓] YOLO 모델 로드 완료
  [INFO] 감지 가능한 객체 클래스:
        - 0: go_straight
        - 1: turn_left
        - 2: turn_right
        ...

==================================================
🎯 [객체 감지] 15:30:45
  📌 객체: turn_left
  📏 크기: 15234
  🎭 신뢰도: 89.5%
  💾 방향 표지판 → 큐에 저장 예정
  📝 lane_tracer가 교차로에서 실행할 예정
==================================================
```

## 🔄 시스템 상태 모니터링

main.py 실행 시 1초마다 시스템 상태가 출력됩니다:
```
[상태] 14:52:31
  차량 상태: 주행중
  라인 인식: 양쪽 라인 감지
  detector 활성: True
  활성 객체: turn_left
  저장된 표지판: 2개
```

## 📝 추가 참고사항

### 라인 트레이싱 조정
- HSV 범위 조정이 필요한 경우 lane_tracer.py의 YELLOW_LINE_HSV 값 수정
- 모터 속도 조정: SPEED_DEFAULT, SPEED_TURN 값 수정

### 객체 감지 민감도 조정
- object_detector.py의 CONF_THRESHOLD 값 조정 (기본 0.7)
- MIN_AREA 값으로 최소 감지 크기 조정 (기본 5000)

### 성능 최적화
- 프레임 처리 간격: lane_tracer.py의 frame_count % 3 값 조정
- 객체 감지 간격: object_detector.py의 time.sleep(0.2) 값 조정