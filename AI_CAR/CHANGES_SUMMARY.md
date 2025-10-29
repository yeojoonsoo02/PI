# 검은 선 → 노란 선 변경 요약 ⚡

## 🎯 핵심 변경 3줄 요약

1. **색공간 변경**: `BGR → Grayscale` ❌ / `BGR → HSV` ✅
2. **감지 방법**: `threshold()` ❌ / `inRange()` ✅
3. **추가 필요**: `import numpy as np` 추가

---

## 📝 코드 비교

### 변경 전 (검은 선) - 5_3_7.py
```python
# 57-65번 줄
gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
blur = cv2.GaussianBlur(gray,(5,5),0)
ret,thresh1 = cv2.threshold(blur,130,255,cv2.THRESH_BINARY_INV)
mask = cv2.erode(thresh1, None, iterations=2)
mask = cv2.dilate(mask, None, iterations=2)
```

### 변경 후 (노란 선) - 5_3_7_yellow.py
```python
# 1번 줄에 추가
import numpy as np

# 58-71번 줄
hsv = cv2.cvtColor(crop_img, cv2.COLOR_BGR2HSV)
lower_yellow = np.array([20, 100, 100])
upper_yellow = np.array([30, 255, 255])
mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
mask = cv2.erode(mask, None, iterations=2)
mask = cv2.dilate(mask, None, iterations=2)
```

---

## ⚙️ 수정 방법 (2가지)

### 방법 1: 새 파일 사용 (권장 ✅)
```bash
cd AI_CAR
python 5_3_7_yellow.py
```
→ 이미 노란색 설정이 적용된 새 파일 사용

### 방법 2: 직접 수정
1. `5_3_7.py` 열기
2. 맨 위에 `import numpy as np` 추가
3. 57-61번 줄 삭제
4. 아래 코드로 교체:
```python
hsv = cv2.cvtColor(crop_img, cv2.COLOR_BGR2HSV)
lower_yellow = np.array([20, 100, 100])
upper_yellow = np.array([30, 255, 255])
mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
```

---

## 🎨 색상 값 찾는 방법

### 기본 설정으로 안 되면?
```bash
python color_calibration.py
```

1. 트랙바로 HSV 값 조정
2. Mask 창에서 노란색 선만 흰색으로 보이도록
3. `q` 눌러 최종 값 확인
4. 출력된 값을 코드에 적용

---

## 🔍 다른 색상으로 변경하려면?

### 노란색 (기본)
```python
lower = np.array([20, 100, 100])
upper = np.array([30, 255, 255])
```

### 빨간색
```python
# 빨간색은 2개 범위 필요
lower1 = np.array([0, 100, 100])
upper1 = np.array([10, 255, 255])
mask1 = cv2.inRange(hsv, lower1, upper1)

lower2 = np.array([170, 100, 100])
upper2 = np.array([179, 255, 255])
mask2 = cv2.inRange(hsv, lower2, upper2)

mask = cv2.bitwise_or(mask1, mask2)
```

### 파란색
```python
lower = np.array([100, 100, 100])
upper = np.array([130, 255, 255])
```

### 녹색
```python
lower = np.array([40, 50, 50])
upper = np.array([80, 255, 255])
```

### 흰색
```python
lower = np.array([0, 0, 200])
upper = np.array([179, 30, 255])
```

---

## ✅ 테스트 체크리스트

실행 전 확인:
- [ ] `import numpy as np` 추가했는가?
- [ ] HSV 색공간으로 변환했는가?
- [ ] `cv2.inRange()` 사용했는가?
- [ ] 노란색 범위 값이 올바른가?

실행 후 확인:
- [ ] mask 창에서 노란색 선이 흰색으로 보이는가?
- [ ] 배경은 검은색으로 나타나는가?
- [ ] 차량이 노란색 선을 따라가는가?

---

## 📁 파일 목록

| 파일명 | 설명 |
|--------|------|
| `5_3_7.py` | 원본 (검은 선) |
| `5_3_7_yellow.py` | 노란 선 버전 ⭐ |
| `color_calibration.py` | HSV 값 찾기 도구 |
| `YELLOW_LINE_GUIDE.md` | 상세 가이드 |
| `CHANGES_SUMMARY.md` | 이 파일 |

---

## 🚀 빠른 시작

```bash
# 1. 노란색 선 따라가기 (기본 설정)
cd AI_CAR
python 5_3_7_yellow.py

# 2. 색상 값이 안 맞으면 캘리브레이션
python color_calibration.py
# → 트랙바 조정 → q 눌러 값 확인 → 5_3_7_yellow.py에 적용

# 3. 다시 실행
python 5_3_7_yellow.py
```

---

## 💡 핵심 개념

### HSV란?
- **H (Hue)**: 색상 (빨강=0, 노랑=30, 초록=60, 파랑=120)
- **S (Saturation)**: 채도 (0=회색, 255=선명)
- **V (Value)**: 명도 (0=검정, 255=밝음)

### 왜 HSV를 사용하나?
- 밝기 변화에 강함
- 색상으로 구분 가능
- 조명 영향 적음

### Grayscale vs HSV
| 구분 | Grayscale | HSV |
|-----|-----------|-----|
| 밝기만 | ✅ | ❌ |
| 색상 구분 | ❌ | ✅ |
| 조명 변화 | 매우 민감 | 덜 민감 |
| 노란색 감지 | 어려움 | 쉬움 |

---

## 🔧 문제 해결

### 감지가 안 돼요!
→ `python color_calibration.py` 실행해서 값 찾기

### 배경도 같이 감지돼요!
→ `S_min`을 높이기 (100 → 150)

### 조명 바뀌면 안 돼요!
→ `V_min`을 낮추기 (100 → 50)

### 노이즈가 많아요!
→ `iterations` 증가 (2 → 3)

---

**더 자세한 내용은 `YELLOW_LINE_GUIDE.md` 참조**
