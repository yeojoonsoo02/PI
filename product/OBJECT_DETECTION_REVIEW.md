# 객체 인식 시스템 전체 리뷰
## 📅 2024-11-13

## 🔄 시스템 구조 분석

### 1. **데이터 흐름**
```
카메라 → lane_tracer.py → shared_state → object_detector.py → 객체 감지
                ↓                              ↓
           라인 트레이싱                   YOLO 모델 처리
                ↓                              ↓
            큐 시스템 ← shared_state ← 감지 결과
```

### 2. **스레드 구조 (main.py)**
- **Lane Thread**: `lane_follow_loop()` 실행 (daemon=True)
- **Detector Thread**: `object_detect_loop()` 실행 (daemon=True)
- **Main Thread**: 모니터링 및 상태 출력 (1초마다)

## ✅ 정상 작동 부분

### 1. **프레임 공유 메커니즘**
```python
# lane_tracer.py (675-678줄)
if OBJECT_DETECTION_ENABLED and frame_count % 3 == 0:
    with shared_state.lock:
        shared_state.latest_frame = frame.copy()
```
- 3프레임마다 한 번씩 프레임 전달 ✅
- Thread-safe lock 사용 ✅
- copy()로 독립적인 프레임 전달 ✅

### 2. **객체 상태 업데이트**
```python
# object_detector.py (168-177줄)
for obj_name in shared_state.KNOWN_OBJECTS:
    shared_state.object_state[obj_name] = False

if detected_label:
    if detected_label in shared_state.KNOWN_OBJECTS:
        shared_state.object_state[detected_label] = True
        shared_state.object_area[detected_label] = nearest_area
        shared_state.object_last_seen[detected_label] = now
```
- 매 프레임마다 상태 초기화 ✅
- 감지된 객체만 True로 설정 ✅
- 면적과 시간 정보 저장 ✅

### 3. **표지판 큐 시스템**
```python
# lane_tracer.py (420-439줄)
def store_direction_signs(frame_count=0):
    # 방향 표지판 감지 시 큐에 저장
    recognized_signs.append(sign_info)
```
- 쿨다운 시간(3초)으로 중복 방지 ✅
- deque(maxlen=5)로 메모리 관리 ✅

## ⚠️ 잠재적 문제점 및 개선 사항

### 1. **모델 파일 경로 문제**
```python
# object_detector.py (60-68줄)
if not DETECTOR_PATH:
    while True:
        time.sleep(1)  # 무한 대기
```
**문제**: 모델이 없으면 스레드가 무한 대기
**개선안**:
```python
if not DETECTOR_PATH:
    shared_state.detector_active = False  # 상태 표시
    return  # 스레드 종료
```

### 2. **프레임 동기화 문제**
- lane_tracer: 3프레임마다 전송
- object_detector: 0.2초마다 처리 (약 5FPS)
- **불일치**: 일부 프레임 놓칠 가능성

**개선안**:
```python
# 동기화 개선
FRAME_INTERVAL = 5  # 양쪽 모두 5프레임마다
```

### 3. **ROI 설정 하드코딩**
```python
# object_detector.py (102-104줄)
roi_rgb = frame_rgb[:, width // 2:]  # 오른쪽 절반만
```
**문제**: 왼쪽 표지판 감지 불가
**개선안**: 전체 프레임 또는 설정 가능한 ROI

### 4. **신뢰도 임계값 불일치**
- Detector: `CONF_THRESHOLD = 0.7`
- Classifier: `sub_conf < 0.8`
**개선안**: 통일된 임계값 사용

### 5. **에러 처리 부족**
```python
# object_detector.py (118줄)
for box in results[0].boxes:  # results가 비어있으면?
```
**개선안**:
```python
if results and len(results) > 0 and results[0].boxes is not None:
    for box in results[0].boxes:
```

## 🎯 성능 최적화 제안

### 1. **프레임 처리 최적화**
```python
# 현재: BGR → RGB 변환 매번 수행
frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

# 개선: lane_tracer에서 RGB로 전송
shared_state.latest_frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
```

### 2. **불필요한 print 제거**
- 30프레임마다 출력하는 디버그 로그들
- 매 감지마다 출력하는 상세 로그
→ 프로덕션에서는 제거 또는 로그 레벨 설정

### 3. **메모리 관리**
```python
# 현재: 무제한 저장
shared_state.object_last_seen[detected_label] = now

# 개선: 오래된 데이터 정리
if now - shared_state.object_last_seen[obj] > 10:
    del shared_state.object_last_seen[obj]
```

## 📊 전체 평가

### ✅ 잘 작동하는 부분
1. **스레드 간 통신**: shared_state와 lock 잘 활용
2. **표지판 큐 시스템**: 안정적인 저장 및 실행
3. **모델 파일 자동 탐색**: 여러 경로 확인
4. **BGR/RGB 변환**: YOLO 입력 형식 맞춤

### ⚠️ 주의가 필요한 부분
1. **모델 없을 때 처리**: 무한 대기 문제
2. **ROI 하드코딩**: 왼쪽 객체 놓침
3. **프레임 동기화**: 타이밍 불일치
4. **에러 처리**: 예외 상황 대비 부족

### 🚀 권장 개선 우선순위
1. 🔴 **긴급**: 모델 없을 때 무한 대기 수정
2. 🟡 **중요**: ROI 전체 프레임으로 확장
3. 🟢 **개선**: 프레임 동기화 및 성능 최적화

## 💡 결론

**전반적으로 잘 설계된 시스템**이며, 다음과 같은 강점이 있습니다:
- Thread-safe 설계
- 모듈 간 깔끔한 분리
- 실시간 처리 가능한 구조

다만 몇 가지 개선점을 적용하면 더욱 안정적이고 효율적인 시스템이 될 것입니다.