# 색상 시스템 분석 보고서
## 📅 2024-11-13

## ✅ RGB/BGR 변환 체계 검증 결과

### 🎥 카메라 → 라인 트레이싱 색상 흐름
```
1. 카메라 설정 (lane_tracer.py:386)
   - 형식: RGB888
   - 해상도: 640x480

2. 프레임 획득 (lane_tracer.py:396-397)
   - picam2.capture_array() → RGB 프레임
   - cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) → BGR 변환
   - OpenCV 표준 형식으로 변환 ✅

3. HSV 변환 (lane_tracer.py:756, 765, 771)
   - cv2.cvtColor(box, cv2.COLOR_BGR2HSV)
   - BGR → HSV 정확한 변환 ✅

4. 색상 범위 (lane_tracer.py:606-607)
   - 청록색(Cyan) 감지
   - lower: [65, 20, 20]
   - upper: [115, 255, 255]
```

### 🤖 객체 인식 색상 흐름
```
1. 프레임 공유 (lane_tracer → shared_state)
   - BGR 형식으로 저장

2. 객체 감지 모듈 (object_detector.py:115, 122)
   - shared_state에서 BGR 프레임 받음
   - cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB) → RGB 변환
   - YOLO 모델은 RGB를 기대하므로 올바른 변환 ✅
```

## 📊 색상 변환 정합성 평가

| 모듈 | 입력 | 변환 | 출력 | 정확도 |
|------|------|------|------|--------|
| 카메라 | - | - | RGB | ✅ |
| lane_tracer | RGB | RGB→BGR | BGR | ✅ |
| HSV 변환 | BGR | BGR→HSV | HSV | ✅ |
| shared_state | BGR | - | BGR | ✅ |
| object_detector | BGR | BGR→RGB | RGB | ✅ |
| YOLO | RGB | - | - | ✅ |

**결론: 모든 색상 변환이 정확하게 구현되어 있음**

## 🚦 방향 표지판 시스템

### 지원되는 방향 표지판
네, 직진/좌회전/우회전 표지판이 이미 완벽하게 구현되어 있습니다!

| 표지판 | 클래스명 | 동작 | 실행 시점 |
|--------|---------|------|-----------|
| ⬆️ 직진 | go_straight | 1.5초 직진 | 교차로 |
| ⬅️ 좌회전 | turn_left | 1초 좌회전 | 교차로 |
| ➡️ 우회전 | turn_right | 1초 우회전 | 교차로 |

### 방향 표지판 처리 흐름
```
1. 객체 감지 (object_detector.py)
   ↓
2. 클래스명 매핑 (line 156-167)
   - "left" → "turn_left"
   - "right" → "turn_right"
   - "straight" → "go_straight"
   ↓
3. shared_state 업데이트
   ↓
4. lane_tracer가 큐에 저장 (store_direction_signs)
   ↓
5. 교차로 도달 시 실행 (execute_stored_sign)
```

### 실제 구현 코드

#### 1. 표지판 저장 (lane_tracer.py:440-470)
```python
def store_direction_signs(frame_count=0):
    """방향 표지판을 인식하여 큐에 저장만 함"""
    direction_signs = ["go_straight", "turn_left", "turn_right"]

    for sign in direction_signs:
        if obj_state.get(sign):
            sign_info = {
                'type': sign,
                'confidence': conf,
                'time': current_time,
                'timestamp': timestamp,
                'frame': frame_count
            }
            recognized_signs.append(sign_info)
```

#### 2. 표지판 실행 (lane_tracer.py:487-526)
```python
def execute_stored_sign():
    if sign_type == "go_straight":
        print("⬆️ 직진 표지판 → 직진 실행")
        motor_forward()
        time.sleep(1.5)

    elif sign_type == "turn_left":
        print("⬅️ 좌회전 표지판 → 좌회전 실행")
        motor_left(1.0)
        time.sleep(1.0)

    elif sign_type == "turn_right":
        print("➡️ 우회전 표지판 → 우회전 실행")
        motor_right(0.8)
        time.sleep(1.0)
```

## 🎯 시스템 특징

### 1. 스마트 큐 시스템
- 방향 표지판을 미리 감지하여 큐에 저장
- 교차로 도달 시 자동 실행
- 최대 5개까지 저장 (deque(maxlen=5))

### 2. 중복 방지
- 3초 쿨다운으로 같은 표지판 중복 저장 방지
- 마지막 표지판과 비교하여 연속 저장 방지

### 3. 우선순위 시스템
- 즉시 동작: STOP, 신호등, HORN, SLOW
- 교차로 동작: 방향 표지판

## 💡 핵심 포인트

1. **색상 변환**: 모든 모듈에서 올바른 색상 공간 사용 중
2. **방향 표지판**: 이미 완벽하게 구현됨
3. **큐 시스템**: 지능적으로 표지판 저장 및 실행
4. **호환성**: BGR(OpenCV) ↔ RGB(YOLO) 변환 정확

## 🔬 디버그 팁

색상 문제가 발생한다면:
1. 노란색/청록색 라인 감지 문제
   - HSV 범위 조정 필요
   - 현재: H[65-115], S[20-255], V[20-255]

2. 표지판 인식 문제
   - YOLO 모델 클래스 확인
   - 신뢰도 임계값 조정 (현재 0.7)

3. 색상 변환 확인
   - print(frame.shape, frame.dtype)로 형식 확인
   - cv2.imshow()로 시각적 확인