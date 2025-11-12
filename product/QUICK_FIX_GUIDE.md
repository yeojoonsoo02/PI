# 🚨 긴급 해결 가이드 - 객체 인식 안됨 문제

## 문제 원인
**best.pt 모델 파일이 없어서 객체 인식이 전혀 작동하지 않음**

## 즉시 해결 방법

### 방법 1: 모델 파일 자동 설정 (권장) 🔧
```bash
# 1. fix_model.sh 파일 전송
scp fix_model.sh keonha@라즈베리파이IP:/home/keonha/AI_CAR/

# 2. 라즈베리파이에서 실행
ssh keonha@라즈베리파이IP
cd /home/keonha/AI_CAR
chmod +x fix_model.sh
./fix_model.sh
```

### 방법 2: 수동으로 모델 파일 복사 📁

#### 로컬에서 best.pt 파일 전송
```bash
# Mac/Linux에서 실행
scp /Users/yeojoonsoo02/Desktop/Python_Project/PI/best.pt keonha@라즈베리파이IP:/home/keonha/AI_CAR/test/
```

#### 라즈베리파이에서 여러 위치에 복사
```bash
# SSH 접속 후
cd /home/keonha/AI_CAR

# test 디렉토리에 복사
cp best.pt test/best.pt

# product 디렉토리에도 복사 (있다면)
cp best.pt product/best.pt
```

### 방법 3: 최신 코드 업데이트 🔄
```bash
# object_detector.py 파일 업데이트
scp object_detector.py keonha@라즈베리파이IP:/home/keonha/AI_CAR/test/
```

## 확인 방법

### 1. 모델 파일 존재 확인
```bash
ls -la /home/keonha/AI_CAR/test/best.pt
ls -la /home/keonha/AI_CAR/best.pt
```

### 2. 프로그램 실행
```bash
cd /home/keonha/AI_CAR/test
python3 main.py
```

### 3. 정상 작동 로그 확인
```
✅ 정상 로그:
  [INFO] YOLO 모델 파일 검색 중...
  [✓] 모델 파일 발견: /home/keonha/AI_CAR/test/best.pt
  [✓] YOLO 모델 로드 완료
  [INFO] 감지 가능한 객체 클래스:
        - 0: go_straight
        - 1: turn_left
        - 2: turn_right
        - 3: stop
        - 4: slow
        - 5: horn
        - 6: traffic

❌ 문제 로그:
  [⚠️] best.pt 모델 파일을 찾을 수 없음
  [INFO] Object detector 스레드 종료
```

## 실시간 디버그 명령어

### 모델 파일 찾기
```bash
find /home/keonha -name "*.pt" 2>/dev/null
```

### Python에서 직접 테스트
```python
from ultralytics import YOLO
import os

# 모델 파일 확인
if os.path.exists("/home/keonha/AI_CAR/test/best.pt"):
    print("✓ 모델 파일 있음")
    model = YOLO("/home/keonha/AI_CAR/test/best.pt")
    print("✓ 모델 로드 성공")
    print("클래스:", model.names)
else:
    print("✗ 모델 파일 없음")
```

## 체크리스트

- [ ] best.pt 파일이 라즈베리파이에 있는가?
- [ ] 파일 경로가 올바른가? (`/home/keonha/AI_CAR/test/`)
- [ ] 파일 권한이 읽기 가능한가? (`ls -la best.pt`)
- [ ] ultralytics 패키지가 설치되어 있는가? (`pip3 list | grep ultralytics`)

## 완전 초기화 (최후 수단)
```bash
# 1. 기존 파일 삭제
rm -f /home/keonha/AI_CAR/test/*.pt
rm -f /home/keonha/AI_CAR/*.pt

# 2. 새로 전송
scp /Users/yeojoonsoo02/Desktop/Python_Project/PI/best.pt keonha@라즈베리파이IP:/home/keonha/AI_CAR/
scp /Users/yeojoonsoo02/Desktop/Python_Project/PI/best.pt keonha@라즈베리파이IP:/home/keonha/AI_CAR/test/

# 3. 권한 설정
chmod 644 /home/keonha/AI_CAR/best.pt
chmod 644 /home/keonha/AI_CAR/test/best.pt

# 4. 실행
cd /home/keonha/AI_CAR/test
python3 main.py
```

## 예상 결과

모델 파일이 제대로 설정되면:
1. 🎯 표지판 감지 로그가 나타남
2. 🚦 신호등 감지 시 자동 우회전
3. 🛑 STOP 표지판에서 자동 정지
4. 📢 HORN 표지판에서 경적
5. ⬆️⬅️➡️ 방향 표지판 인식 및 저장