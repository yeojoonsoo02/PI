# 라인 트레이싱 안정성 개선 사항

## 📅 2024-11-12 안정성 개선

### 🔍 분석된 문제점

1. **픽셀 임계값 혼란**
   - 고정값이라고 했지만 계속 동적 계산
   - MIN_PIXEL_RATIO 사용 안함

2. **회전 제어 복잡도**
   - turn_intensity 계산이 너무 복잡
   - one_side_missing 로직이 복잡하고 불안정

3. **상태 관리 복잡도**
   - 여러 상태 변수가 얽혀있음
   - 불필요한 변수들

### ✅ 개선 내용

#### 1. **파라미터 정리 및 고정**
```python
# 이전 (복잡하고 동적)
PIXEL_THRESHOLD = int(BOX_WIDTH * BOX_HEIGHT * 2 * MIN_PIXEL_RATIO)
CENTER_THRESHOLD = int(center_box_width * center_box_height * 0.3)

# 개선 (단순하고 고정)
PIXEL_THRESHOLD = 800   # 고정값 (더 민감하게 조정)
CENTER_THRESHOLD = 5000 # 고정값
BALANCE_THRESHOLD = 0.30 # 고정값
```

#### 2. **회전 제어 단순화**
```python
# 이전 (복잡한 계산)
turn_intensity = min(1.0, diff / 0.5)
if right_pixels < 50:
    if one_side_missing_time is None or ...
    # 복잡한 로직...

# 개선 (단순한 3단계)
if diff > 0.6:        # 큰 편차
    motor_right(1.0)  # 강한 회전
elif diff > 0.4:      # 중간 편차
    motor_right(0.7)  # 중간 회전
else:                 # 작은 편차
    motor_right(0.5)  # 약한 회전
```

#### 3. **불필요한 코드 제거**
- subprocess import 제거
- one_side_missing 관련 변수/로직 제거
- LINE_LOST_THRESHOLD 제거
- 동적 임계값 계산 제거

#### 4. **안정성 향상 파라미터**
```python
# 주요 파라미터 (조정 가능)
PIXEL_THRESHOLD = 800        # 라인 감지 민감도 (낮을수록 민감)
BALANCE_THRESHOLD = 0.30     # 직진 판단 기준 (낮을수록 민감)
TURN_THRESHOLD_STRONG = 0.6  # 강한 회전 기준
TURN_THRESHOLD_MEDIUM = 0.4  # 중간 회전 기준
```

### 🎯 조정 가이드

#### 라인을 잘 못 찾는 경우:
```python
PIXEL_THRESHOLD = 600  # 더 낮춰서 민감하게
```

#### 회전이 너무 급격한 경우:
```python
# motor_left/right 함수의 강도 조절
motor_right(0.8)  # 1.0 대신 0.8
motor_right(0.5)  # 0.7 대신 0.5
motor_right(0.3)  # 0.5 대신 0.3
```

#### 직진이 불안정한 경우:
```python
BALANCE_THRESHOLD = 0.25  # 더 낮춰서 민감하게
```

### 📊 개선 결과

1. **코드 복잡도**: 약 30% 감소
2. **상태 변수**: 5개 → 2개로 감소
3. **회전 로직**: 27줄 → 9줄로 단순화
4. **예측 가능성**: 크게 향상

### 🚀 테스트 권장사항

1. **기본 테스트**
   ```bash
   python3 lane_tracer.py
   ```

2. **파라미터 조정 테스트**
   - PIXEL_THRESHOLD: 600, 800, 1000 순서로 테스트
   - 가장 안정적인 값 찾기

3. **회전 강도 테스트**
   - 곡선 구간에서 회전 부드러움 확인
   - 필요시 motor_left/right 강도 조절

### ⚠️ 주의사항

- 조명 환경에 따라 PIXEL_THRESHOLD 조정 필요
- 트랙 폭에 따라 BALANCE_THRESHOLD 조정 필요
- 바닥 재질에 따라 회전 강도 조정 필요