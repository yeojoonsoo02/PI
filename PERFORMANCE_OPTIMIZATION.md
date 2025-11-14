# ⚡ Line Tracer 성능 최적화 가이드

## 🔧 완료된 수정사항

### 1. 변수 초기화 오류 해결 ✅
```python
# 추가된 초기화 코드 (line 480-495)
action = "STOP"  # 현재 동작 상태 초기화
width = 640
height = 480
BOX_WIDTH = int(width * BOX_WIDTH_RATIO)
BOX_HEIGHT = int(height * BOX_HEIGHT_RATIO)
```

---

## 🚀 성능 최적화 제안

### 1. 차량 정지 시 프레임 처리 최적화

**현재 문제점**:
- 차량 정지 중에도 라인 인식 계산 수행
- 불필요한 CPU 사용

**최적화 코드**:
```python
# line 565 부근 수정
if vehicle_stopped:
    # 객체 인식만 계속 수행
    if OBJECT_DETECTION_ENABLED and frame_count % 3 == 0:
        try:
            with shared_state.lock:
                shared_state.latest_frame = frame.copy()
        except:
            pass

    # 정지 상태 로그 (3초마다)
    current_time = time.time()
    if current_time - last_stop_log_time >= 3.0:
        runtime = int(current_time - start_time)
        print(f"[{runtime:3d}s] 🔴 차량 정지 중 ({stop_reason})")
        last_stop_log_time = current_time

    # 통계만 업데이트하고 다음 프레임으로
    action_stats["STOP"] += 1
    time.sleep(0.02)
    continue  # 라인 처리 건너뛰기
```

**예상 성능 향상**: CPU 사용률 20-30% 감소

---

### 2. 프레임 처리 파이프라인 최적화

**최적화 전략**:
```python
# ROI 사전 계산 및 캐싱
class ROIManager:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.update_rois()

    def update_rois(self):
        # ROI 좌표 사전 계산
        self.left_roi = self.calculate_left_roi()
        self.right_roi = self.calculate_right_roi()
        self.center_roi = self.calculate_center_roi()

    def process_frame(self, frame):
        # 캐시된 ROI 사용
        left_box = frame[self.left_roi]
        right_box = frame[self.right_roi]
        center_box = frame[self.center_roi]
        return left_box, right_box, center_box
```

---

### 3. HSV 변환 최적화

**현재**: 각 박스별로 개별 HSV 변환
```python
hsv_left = cv2.cvtColor(left_box, cv2.COLOR_BGR2HSV)
hsv_right = cv2.cvtColor(right_box, cv2.COLOR_BGR2HSV)
hsv_center = cv2.cvtColor(center_box, cv2.COLOR_BGR2HSV)
```

**최적화**: 전체 프레임 한 번만 변환
```python
# 전체 프레임 HSV 변환 (한 번만)
hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

# ROI 추출
hsv_left = hsv_frame[left_y1:left_y2, left_x1:left_x2]
hsv_right = hsv_frame[right_y1:right_y2, right_x1:right_x2]
hsv_center = hsv_frame[center_y1:center_y2, center_x1:center_x2]
```

**예상 성능 향상**: 프레임 처리 시간 30% 감소

---

### 4. 노이즈 제거 최적화

**현재**: 각 마스크별로 개별 처리
```python
kernel = np.ones((3, 3), np.uint8)
mask_left = cv2.erode(mask_left, kernel, iterations=2)
mask_left = cv2.dilate(mask_left, kernel, iterations=3)
```

**최적화**: 커널 사전 생성 및 재사용
```python
# 초기화 시 커널 생성
self.kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
self.kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

# 처리 시 재사용
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel_erode)
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kernel_dilate)
```

---

### 5. 동적 프레임 스킵

```python
class DynamicFrameSkipper:
    def __init__(self):
        self.skip_rate = 1
        self.last_action = "STOP"
        self.stable_count = 0

    def should_process(self, frame_count):
        # 안정적인 직진 시 프레임 스킵 증가
        if self.last_action == "FORWARD":
            self.stable_count += 1
            if self.stable_count > 30:  # 30프레임 안정
                self.skip_rate = 2  # 2프레임마다 처리
        else:
            self.stable_count = 0
            self.skip_rate = 1  # 모든 프레임 처리

        return frame_count % self.skip_rate == 0
```

---

## 📊 성능 측정 코드

```python
import time
import psutil
import threading

class PerformanceMonitor:
    def __init__(self):
        self.frame_times = []
        self.cpu_usage = []
        self.memory_usage = []
        self.monitoring = True

    def start_monitoring(self):
        def monitor():
            process = psutil.Process()
            while self.monitoring:
                self.cpu_usage.append(process.cpu_percent())
                self.memory_usage.append(process.memory_info().rss / 1024 / 1024)
                time.sleep(1)

        thread = threading.Thread(target=monitor)
        thread.daemon = True
        thread.start()

    def log_frame_time(self, start_time):
        frame_time = time.time() - start_time
        self.frame_times.append(frame_time)

    def print_stats(self):
        if self.frame_times:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            avg_fps = 1 / avg_frame_time if avg_frame_time > 0 else 0

            print(f"\n성능 통계:")
            print(f"  평균 FPS: {avg_fps:.1f}")
            print(f"  평균 프레임 시간: {avg_frame_time*1000:.1f}ms")

        if self.cpu_usage:
            print(f"  평균 CPU 사용률: {sum(self.cpu_usage)/len(self.cpu_usage):.1f}%")

        if self.memory_usage:
            print(f"  평균 메모리 사용: {sum(self.memory_usage)/len(self.memory_usage):.1f}MB")
```

---

## 🎯 적용 우선순위

### 즉시 적용 (효과 높음, 구현 쉬움):
1. ✅ 변수 초기화 (완료)
2. ⚡ 차량 정지 시 프레임 건너뛰기
3. ⚡ 전체 프레임 HSV 변환

### 단기 적용 (효과 중간, 구현 보통):
1. 💡 ROI 관리자 클래스 도입
2. 💡 커널 사전 생성 및 재사용
3. 💡 동적 프레임 스킵

### 장기 적용 (효과 높음, 구현 복잡):
1. 🔧 멀티스레딩 프레임 처리
2. 🔧 GPU 가속 (OpenCV CUDA)
3. 🔧 신경망 기반 라인 검출

---

## 📈 예상 성능 개선

| 최적화 항목 | CPU 감소 | FPS 증가 | 구현 난이도 |
|------------|----------|----------|------------|
| 정지 시 건너뛰기 | 20-30% | +5-10 | ⭐ |
| HSV 최적화 | 10-15% | +10-15 | ⭐⭐ |
| ROI 캐싱 | 5-10% | +5-10 | ⭐⭐ |
| 동적 프레임 스킵 | 15-25% | +10-20 | ⭐⭐⭐ |
| 멀티스레딩 | 30-40% | +20-30 | ⭐⭐⭐⭐ |

---

## 💾 메모리 최적화

### 현재 메모리 사용 패턴:
- 매 프레임 frame.copy() 호출
- 임시 변수들의 누적
- 큰 배열의 중복 생성

### 최적화 방안:
```python
# 프레임 복사 최소화
if OBJECT_DETECTION_ENABLED and frame_count % 3 == 0:
    # copy() 대신 참조 사용 (읽기 전용)
    with shared_state.lock:
        shared_state.latest_frame = frame  # copy() 제거
        shared_state.frame_id = frame_count  # 프레임 ID로 추적

# 임시 변수 재사용
class FrameProcessor:
    def __init__(self):
        # 재사용 가능한 버퍼 사전 할당
        self.hsv_buffer = np.empty((480, 640, 3), dtype=np.uint8)
        self.mask_buffer = np.empty((480, 640), dtype=np.uint8)
```

---

## 🔍 디버깅 및 프로파일링

### 병목 지점 찾기:
```python
import cProfile
import pstats

# 프로파일링 시작
profiler = cProfile.Profile()
profiler.enable()

# ... 메인 루프 실행 ...

# 프로파일링 종료 및 결과 출력
profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)  # 상위 10개 함수
```

---

## ✅ 체크리스트

- [x] 변수 초기화 오류 수정
- [ ] 차량 정지 최적화 적용
- [ ] HSV 변환 통합
- [ ] ROI 캐싱 구현
- [ ] 성능 모니터링 추가
- [ ] 메모리 사용 최적화
- [ ] 프로파일링 수행
- [ ] 동적 프레임 스킵 구현

---

작성일: 2024년 12월
최적화 가이드 by Claude Code Assistant