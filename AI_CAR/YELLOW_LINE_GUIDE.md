# 노란색 라인 감지 변경 가이드 🟨

## 핵심 변경 사항

### 검은 선 → 노란 선 변경 방법

#### ❌ 기존 코드 (검은 선)
```python
# 57-61번 줄
gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
blur = cv2.GaussianBlur(gray,(5,5),0)
ret,thresh1 = cv2.threshold(blur,130,255,cv2.THRESH_BINARY_INV)
mask = cv2.erode(thresh1, None, iterations=2)
mask = cv2.dilate(mask, None, iterations=2)
```

#### ✅ 새 코드 (노란 선)
```python
# 57-71번 줄
# BGR을 HSV로 변환
hsv = cv2.cvtColor(crop_img, cv2.COLOR_BGR2HSV)

# 노란색 범위 설정 (HSV)
lower_yellow = np.array([20, 100, 100])
upper_yellow = np.array([30, 255, 255])

# 노란색 마스크 생성
mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

# 노이즈 제거
mask = cv2.erode(mask, None, iterations=2)
mask = cv2.dilate(mask, None, iterations=2)
cv2.imshow('mask',mask)
```

## 변경 이유 및 원리

### 🎨 색상 감지 방식 차이

| 구분 | 검은 선 | 노란 선 |
|-----|--------|---------|
| 색공간 | Grayscale (밝기만) | HSV (색상+채도+명도) |
| 감지 방법 | 임계값 (밝기 130 이하) | 색상 범위 (H=20-30) |
| 이진화 | THRESH_BINARY_INV | inRange |

### 📊 HSV 색공간 설명

**HSV란?**
- **H (Hue)**: 색상 (0-179) - 노란색은 약 20-30
- **S (Saturation)**: 채도 (0-255) - 선명함 정도
- **V (Value)**: 명도 (0-255) - 밝기

**노란색 범위:**
```python
lower_yellow = np.array([20, 100, 100])  # H=20, S=100, V=100
upper_yellow = np.array([30, 255, 255])  # H=30, S=255, V=255
```

## 사용 방법

### 방법 1: 기본 노란색 설정 사용
```bash
cd AI_CAR
python 5_3_7_yellow.py
```

기본 설정으로 실행하여 테스트합니다.

### 방법 2: 색상 범위 캘리브레이션
```bash
cd AI_CAR
python color_calibration.py
```

트랙바를 조정하여 최적의 HSV 값을 찾습니다.

## 🔧 색상 캘리브레이션 방법

### Step 1: 캘리브레이션 도구 실행
```bash
python color_calibration.py
```

### Step 2: 트랙바 조정
5개의 윈도우가 열립니다:
- **Original**: 원본 영상
- **Cropped**: 하단 절반 (처리 영역)
- **HSV**: HSV 색공간 변환 결과
- **Mask**: 노란색 마스크 (이진화 결과)
- **Result**: 필터링된 결과

**Trackbars 윈도우:**
- `H_min`, `H_max`: 색상(Hue) 범위
- `S_min`, `S_max`: 채도(Saturation) 범위
- `V_min`, `V_max`: 명도(Value) 범위

### Step 3: 최적 값 찾기
1. **Mask 창**에서 노란색 선만 흰색으로 보이도록 조정
2. 배경은 검은색으로 나타나야 함
3. `q` 키를 눌러 종료하면 최종 값 출력

**출력 예시:**
```
최종 HSV 값:
lower_yellow = np.array([25, 120, 80])
upper_yellow = np.array([35, 255, 255])
```

### Step 4: 값 적용
찾은 값을 `5_3_7_yellow.py` 파일에 적용:

```python
# 63-64번 줄 수정
lower_yellow = np.array([25, 120, 80])    # 캘리브레이션에서 찾은 값
upper_yellow = np.array([35, 255, 255])   # 캘리브레이션에서 찾은 값
```

## 다양한 노란색 설정

### 밝은 노란색 (밝은 환경)
```python
lower_yellow = np.array([20, 100, 150])
upper_yellow = np.array([30, 255, 255])
```

### 어두운 노란색 (어두운 환경)
```python
lower_yellow = np.array([15, 80, 50])
upper_yellow = np.array([35, 255, 200])
```

### 주황빛 노란색
```python
lower_yellow = np.array([10, 100, 100])
upper_yellow = np.array([25, 255, 255])
```

### 연한 노란색
```python
lower_yellow = np.array([20, 50, 100])
upper_yellow = np.array([30, 150, 255])
```

## 다른 색상으로 변경하려면?

### 🔴 빨간색 선
```python
# 빨간색은 HSV에서 두 범위로 나뉨
lower_red1 = np.array([0, 100, 100])
upper_red1 = np.array([10, 255, 255])
mask1 = cv2.inRange(hsv, lower_red1, upper_red1)

lower_red2 = np.array([170, 100, 100])
upper_red2 = np.array([179, 255, 255])
mask2 = cv2.inRange(hsv, lower_red2, upper_red2)

mask = cv2.bitwise_or(mask1, mask2)
```

### 🔵 파란색 선
```python
lower_blue = np.array([100, 100, 100])
upper_blue = np.array([130, 255, 255])
mask = cv2.inRange(hsv, lower_blue, upper_blue)
```

### 🟢 녹색 선
```python
lower_green = np.array([40, 50, 50])
upper_green = np.array([80, 255, 255])
mask = cv2.inRange(hsv, lower_green, upper_green)
```

### ⚪ 흰색 선
```python
lower_white = np.array([0, 0, 200])
upper_white = np.array([179, 30, 255])
mask = cv2.inRange(hsv, lower_white, upper_white)
```

## 트러블슈팅

### 문제 1: 노란색이 감지 안 됨
**원인:** HSV 범위가 실제 노란색과 다름

**해결:**
1. `color_calibration.py` 실행
2. `H_min`, `H_max` 트랙바 조정
3. Mask 창에서 노란색 선이 흰색으로 보일 때까지 조정

### 문제 2: 배경도 같이 감지됨
**원인:** S(채도)와 V(명도) 범위가 너무 넓음

**해결:**
1. `S_min` 트랙바를 높임 (100 → 150)
2. `V_min` 트랙바를 높임 (100 → 150)
3. 더 선명하고 밝은 영역만 감지되도록 조정

### 문제 3: 조명 변화에 민감함
**원인:** V(명도) 범위가 좁음

**해결:**
```python
# V_min을 낮춰서 어두운 노란색도 감지
lower_yellow = np.array([20, 100, 50])   # V_min: 100 → 50
upper_yellow = np.array([30, 255, 255])
```

### 문제 4: 노이즈가 많이 감지됨
**원인:** Erode/Dilate 반복 횟수 부족

**해결:**
```python
# iterations 값을 증가
mask = cv2.erode(mask, None, iterations=3)   # 2 → 3
mask = cv2.dilate(mask, None, iterations=3)  # 2 → 3
```

## 성능 비교

| 항목 | 검은 선 | 노란 선 |
|-----|--------|---------|
| 처리 속도 | 빠름 | 약간 느림 |
| 조명 민감도 | 매우 높음 | 중간 |
| 색상 구분 | 불가능 | 가능 |
| 노이즈 | 많음 | 적음 |
| 설정 난이도 | 쉬움 | 중간 |

## 추가 개선 사항

### 1. 적응형 임계값
조명 변화에 자동 대응:
```python
mean_v = hsv[:,:,2].mean()  # V 채널 평균
v_min = max(50, mean_v - 100)
lower_yellow = np.array([20, 100, v_min])
```

### 2. 다중 색상 감지
노란색 + 흰색 동시 감지:
```python
mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
mask_white = cv2.inRange(hsv, lower_white, upper_white)
mask = cv2.bitwise_or(mask_yellow, mask_white)
```

### 3. 가우시안 블러 추가
노이즈 감소:
```python
hsv = cv2.cvtColor(crop_img, cv2.COLOR_BGR2HSV)
hsv = cv2.GaussianBlur(hsv, (5, 5), 0)  # 블러 추가
mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
```

## 파일 목록

- **`5_3_7_yellow.py`** - 노란색 선 감지 메인 코드
- **`color_calibration.py`** - HSV 값 캘리브레이션 도구
- **`YELLOW_LINE_GUIDE.md`** - 이 가이드 문서

## 참고 자료

### HSV 색상표 (OpenCV 기준)
- 빨강: 0-10, 170-179
- 주황: 10-25
- **노랑: 25-35** ⭐
- 초록: 35-85
- 청록: 85-100
- 파랑: 100-130
- 보라: 130-170

조명과 카메라에 따라 ±5 정도 차이가 있을 수 있습니다.
