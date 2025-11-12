# 부드러운 주행 및 객체 인식 개선
## 📅 2024-11-12

### 🎯 해결한 문제들

#### 1. **객체 인식이 작동하지 않음 ✅**
**문제**: 표지판을 감지해도 큐에 저장되지 않음
**원인**: `object_state` 업데이트 누락
**해결**:
- 감지된 객체의 `object_state`를 True로 설정
- 각 표지판별 상태 업데이트 추가
- 객체 활성 상태 로그 추가

#### 2. **라인 트레이싱이 급격함 ✅**
**문제**: LEFT/RIGHT/FORWARD가 너무 자주 급격하게 변함
**원인**: 고정 회전 강도(0.5, 0.7, 1.0)만 사용
**해결**:
- diff에 비례한 회전 강도 (0.3 ~ 0.9)
- 이전 상태와 현재 상태 스무딩 적용
- 방향 전환 시 부드러운 전환

### 🔧 주요 개선 사항

#### 1. **객체 인식 상태 업데이트**
```python
# 모든 object_state를 False로 초기화
for obj_name in shared_state.KNOWN_OBJECTS:
    shared_state.object_state[obj_name] = False

# 감지된 객체의 object_state를 True로 설정
if detected_label:
    if detected_label in shared_state.KNOWN_OBJECTS:
        shared_state.object_state[detected_label] = True
        shared_state.object_area[detected_label] = nearest_area
        shared_state.object_last_seen[detected_label] = now
```

#### 2. **부드러운 회전 로직**
```python
# diff에 비례한 회전 강도 계산
raw_intensity = 0.3 + (diff * 0.6)  # 0.3 ~ 0.9
raw_intensity = min(0.9, raw_intensity)

# 스무딩 적용 (이전과 현재의 가중 평균)
if prev_action == current_action:
    current_intensity = (SMOOTHING_FACTOR * prev_intensity) +
                       ((1 - SMOOTHING_FACTOR) * raw_intensity)
else:
    current_intensity = raw_intensity * 0.7  # 방향 전환 시 부드럽게
```

### 📊 개선 파라미터

| 파라미터 | 이전 값 | 새로운 값 | 효과 |
|---------|---------|-----------|------|
| BALANCE_THRESHOLD | 0.30 | 0.15 | 더 민감한 균형 감지 |
| SMOOTHING_FACTOR | - | 0.6 | 이전 상태 60% 반영 |
| 회전 강도 | 0.5/0.7/1.0 | 0.3 ~ 0.9 | 연속적 조정 |
| 최소 회전 강도 | - | 0.3 | 부드러운 최소 회전 |
| 최대 회전 강도 | 1.0 | 0.9 | 과도한 회전 방지 |

### 🚗 부드러운 주행 특징

#### Before (이전)
```
↑ FORWARD → ← LEFT → ↑ FORWARD → → RIGHT
(급격한 전환, 고정 강도)
```

#### After (개선 후)
```
↑ FORWARD → ← LEFT (0.35) → ← LEFT (0.42) → ← LEFT (0.38) → ↑ FORWARD
(점진적 전환, 가변 강도)
```

### 📈 새로운 로그 출력

#### 회전 강도 표시
```
[36s] F:820 | L:5630 R:11082 | ... | → RIGHT (0.45)
[37s] F:830 | L:6029 R:11718 | ... | → RIGHT (0.48)
[37s] F:840 | L:8545 R:10910 | ... | ↑ FORWARD
```

#### 객체 인식 상태
```
[객체 활성] turn_left, stop
[표지판 큐] 2개 저장됨
```

### 🎮 조정 가이드

#### 더 부드럽게 하려면:
```python
SMOOTHING_FACTOR = 0.7  # 더 높게 (0.6 → 0.7)
# 이전 상태를 더 많이 반영
```

#### 더 민감하게 하려면:
```python
SMOOTHING_FACTOR = 0.4  # 더 낮게 (0.6 → 0.4)
# 현재 상태를 더 많이 반영
```

#### 회전 강도 조정:
```python
# 최소 회전 강도
raw_intensity = 0.2 + (diff * 0.6)  # 0.3 → 0.2

# 최대 회전 강도
raw_intensity = min(0.8, raw_intensity)  # 0.9 → 0.8
```

### ✅ 개선 효과

1. **객체 인식 정상 작동**: 표지판 감지 및 큐 저장 확인
2. **부드러운 라인 트레이싱**: 급격한 변화 감소
3. **회전 강도 시각화**: 로그에서 강도 확인 가능
4. **상태 모니터링**: 객체 활성 상태 실시간 확인

### 💡 추가 개선 제안

1. **PID 제어기 도입**: 더 정교한 제어
2. **예측 알고리즘**: 라인 방향 예측
3. **적응형 파라미터**: 속도에 따른 자동 조정
4. **카메라 각도 보정**: 원근 왜곡 보정