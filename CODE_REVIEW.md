# dual_roi_line_tracer.py 코드 리뷰 📋

## 📊 전체 평가

| 항목 | 점수 | 평가 |
|-----|------|------|
| **코드 구조** | ⭐⭐⭐⭐⭐ | 매우 우수 |
| **가독성** | ⭐⭐⭐⭐☆ | 우수 |
| **에러 처리** | ⭐⭐⭐☆☆ | 보통 |
| **성능** | ⭐⭐⭐⭐☆ | 우수 |
| **유지보수성** | ⭐⭐⭐⭐☆ | 우수 |
| **문서화** | ⭐⭐⭐⭐⭐ | 매우 우수 |

**총평**: 전반적으로 잘 작성된 코드입니다. 명확한 구조와 좋은 문서화가 돋보입니다.

---

## ✅ 장점

### 1. 명확한 코드 구조
```python
# 계층적이고 논리적인 함수 구조
open_camera() → detect_line_in_roi() → decide_command() → draw_debug_overlay() → main()
```
- 각 함수가 단일 책임 원칙을 잘 따름
- 함수 이름이 명확하고 의도를 잘 표현

### 2. 우수한 문서화
```python
def detect_line_in_roi(roi, thresh=150, min_pixels=100):
    """
    ROI에서 라인 감지

    Args: ...
    Returns: ...
    """
```
- 모든 함수에 docstring 작성
- 파라미터와 반환값 명시

### 3. 실시간 파라미터 튜닝
```python
# 키보드 입력으로 실시간 조정 가능
elif key == ord('1'):
    thresh = max(60, thresh - 5)
```
- 디버깅과 현장 조정에 매우 유용
- 경계값 검증 포함

### 4. 플랫폼 독립성
```python
USE_GPIO = False  # Mac/Windows에서도 테스트 가능
if USE_GPIO:
    import RPi.GPIO as GPIO
```
- 개발 환경과 실제 환경 분리
- 조건부 import로 의존성 문제 해결

### 5. 우수한 시각화
- 노란색 라인 오버레이
- ROI 박스 색상 구분 (녹색/빨강)
- 실시간 정보 텍스트 표시

---

## ⚠️ 개선이 필요한 부분

### 1. 🔴 심각도: 높음 - 잠재적 크래시

#### 문제: 배열 인덱싱 오류 가능성 (207, 214번 줄)
```python
# 현재 코드
frame[left_y1:left_y2, left_x1:left_x2][yellow_mask_left > 0] = [0, 255, 255]
```

**문제점**:
- `yellow_mask_left`와 `frame[left_y1:left_y2, left_x1:left_x2]`의 크기가 다를 수 있음
- ROI 크기가 매우 작을 때 크래시 가능

**해결 방법**:
```python
# 안전한 방법
roi_region = frame[left_y1:left_y2, left_x1:left_x2]
if roi_region.shape[:2] == yellow_mask_left.shape[:2]:
    roi_region[yellow_mask_left > 0] = [0, 255, 255]
    frame[left_y1:left_y2, left_x1:left_x2] = roi_region
```

---

### 2. 🟡 심각도: 중간 - 에러 처리 부족

#### 문제 A: 카메라 프레임 읽기 실패 (260-262번 줄)
```python
ret, frame = cap.read()
if not ret:
    break  # 그냥 종료만 함
```

**개선안**:
```python
ret, frame = cap.read()
if not ret:
    print("[ERROR] 프레임 읽기 실패. 재시도 중...")
    retry_count = 0
    while retry_count < 3:
        time.sleep(0.1)
        ret, frame = cap.read()
        if ret:
            break
        retry_count += 1
    if not ret:
        print("[ERROR] 카메라 연결 끊김")
        break
```

#### 문제 B: ROI가 빈 영역일 때 (149-151번 줄)
```python
left_roi = frame[roi_y:h, 0:roi_w]
right_roi = frame[roi_y:h, w-roi_w:w]
# ROI가 비어있을 수 있음 (크기 검증 없음)
```

**개선안**:
```python
if roi_h <= 0 or roi_w <= 0:
    print(f"[ERROR] 잘못된 ROI 크기: h={roi_h}, w={roi_w}")
    command = "stop"
    return command, None, None, None, None, {"error": "invalid_roi"}

left_roi = frame[roi_y:h, 0:roi_w]
right_roi = frame[roi_y:h, w-roi_w:w]

# 크기 검증
if left_roi.size == 0 or right_roi.size == 0:
    print("[ERROR] ROI 영역이 비어있음")
    return "stop", None, None, None, None, {"error": "empty_roi"}
```

---

### 3. 🟡 심각도: 중간 - 모터 제어 로직

#### 문제: 급격한 방향 전환 (270-277번 줄)
```python
if command == "forward":
    motor_forward(65)
elif command == "left":
    motor_left(50)
elif command == "right":
    motor_right(50)
# 이전 명령과 상관없이 즉시 실행
```

**개선안 - 스무딩 추가**:
```python
class MotorController:
    def __init__(self):
        self.last_command = "stop"
        self.command_count = 0
        self.min_stable_frames = 3  # 3프레임 연속 같은 명령일 때만 실행

    def execute(self, command):
        if command == self.last_command:
            self.command_count += 1
        else:
            self.command_count = 1
            self.last_command = command

        # 안정화된 명령만 실행
        if self.command_count >= self.min_stable_frames:
            if command == "forward":
                motor_forward(65)
            elif command == "left":
                motor_left(50)
            elif command == "right":
                motor_right(50)
            else:
                motor_stop()
```

---

### 4. 🟢 심각도: 낮음 - 성능 최적화

#### 문제 A: 불필요한 색공간 변환 (205, 212번 줄)
```python
# 매 프레임마다 변환
left_colored = cv2.cvtColor(left_binary, cv2.COLOR_GRAY2BGR)
yellow_mask_left = cv2.inRange(left_colored, (200, 200, 200), (255, 255, 255))
```

**최적화**:
```python
# 이미 이진화된 이미지이므로 직접 사용
yellow_mask_left = left_binary > 200  # 더 빠름
frame[left_y1:left_y2, left_x1:left_x2][yellow_mask_left] = [0, 255, 255]
```

#### 문제 B: 중복된 cv2.waitKey (288번 줄)
```python
key = cv2.waitKey(1) & 0xFF
```
- 매 프레임마다 1ms 대기
- FPS 제한 없음 → CPU 과부하 가능

**개선안**:
```python
# FPS 제한 추가
target_fps = 30
frame_time = 1000 // target_fps  # 약 33ms
key = cv2.waitKey(frame_time) & 0xFF
```

---

### 5. 🟢 심각도: 낮음 - 코드 품질

#### 문제 A: 매직 넘버 (270-275번 줄)
```python
motor_forward(65)  # 65가 무엇을 의미하는가?
motor_left(50)
motor_right(50)
```

**개선안**:
```python
# 상수로 정의
SPEED_FORWARD = 65
SPEED_TURN = 50
SPEED_SLOW = 30

motor_forward(SPEED_FORWARD)
motor_left(SPEED_TURN)
```

#### 문제 B: 하드코딩된 값들 (253-256번 줄)
```python
thresh = 150
roi_height_ratio = 0.3
roi_width_ratio = 0.3
min_pixels = 100
```

**개선안**:
```python
# config 파일이나 클래스로 관리
class Config:
    THRESH_DEFAULT = 150
    ROI_HEIGHT_RATIO = 0.3
    ROI_WIDTH_RATIO = 0.3
    MIN_PIXELS = 100

    THRESH_MIN = 60
    THRESH_MAX = 220
```

---

## 🐛 잠재적 버그

### 1. GPIO 클린업 누락 가능성
```python
# 현재: finally에서 정리
finally:
    cap.release()
    cv2.destroyAllWindows()
    motor_stop()
    if USE_GPIO:
        GPIO.cleanup()
```

**문제**: Ctrl+C 등으로 강제 종료 시 GPIO가 정리 안 될 수 있음

**해결**:
```python
import signal
import sys

def signal_handler(sig, frame):
    print('\n[INFO] 종료 시그널 받음')
    motor_stop()
    if USE_GPIO:
        GPIO.cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
```

### 2. 메모리 누수 가능성
```python
# 윈도우가 계속 생성되지만 정리는 finally에서만
cv2.imshow("Line Tracer", frame)
cv2.imshow("Left ROI", left_binary)
cv2.imshow("Right ROI", right_binary)
```

**현재는 문제 없지만**, 추가 윈도우 생성 시 주의 필요

---

## 🚀 성능 최적화 제안

### 1. 프레임 스킵
```python
# 모든 프레임을 처리하지 않고 필요한 만큼만
frame_skip = 2  # 2프레임마다 1번 처리
frame_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    if frame_count % frame_skip != 0:
        continue  # 스킵

    # 처리...
```

### 2. ROI만 처리
```python
# 전체 프레임 대신 ROI만 읽기
# 현재도 ROI만 처리하지만, 전체 프레임을 읽고 있음
# 카메라 설정에서 관심 영역만 캡처하면 더 빠름
```

### 3. 멀티스레딩
```python
# 카메라 읽기와 처리를 분리
from threading import Thread
import queue

class VideoCapture:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.q = queue.Queue(maxsize=3)
        self.stopped = False

    def start(self):
        Thread(target=self.update, daemon=True).start()
        return self

    def update(self):
        while not self.stopped:
            if not self.q.full():
                ret, frame = self.cap.read()
                if ret:
                    self.q.put(frame)
```

---

## 💡 추가 기능 제안

### 1. 로깅 시스템
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('line_tracer.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("프로그램 시작")
logger.warning("라인 감지 실패")
```

### 2. 설정 저장/로드
```python
import json

def save_config(thresh, roi_height, roi_width, min_pixels):
    config = {
        "thresh": thresh,
        "roi_height_ratio": roi_height,
        "roi_width_ratio": roi_width,
        "min_pixels": min_pixels
    }
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)
    print("[INFO] 설정 저장됨")

def load_config():
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        print("[INFO] 설정 로드됨")
        return config
    except FileNotFoundError:
        print("[INFO] 기본 설정 사용")
        return None

# 사용
# 키 's'를 눌러 저장
elif key == ord('s'):
    save_config(thresh, roi_height_ratio, roi_width_ratio, min_pixels)
```

### 3. 녹화 기능
```python
# 'r' 키로 녹화 시작/종료
recording = False
video_writer = None

if key == ord('r'):
    if not recording:
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        video_writer = cv2.VideoWriter('output.avi', fourcc, 20.0, (w, h))
        recording = True
        print("[INFO] 녹화 시작")
    else:
        video_writer.release()
        recording = False
        print("[INFO] 녹화 종료")

if recording and video_writer:
    video_writer.write(frame)
```

### 4. PID 제어
```python
class PIDController:
    def __init__(self, kp=1.0, ki=0.0, kd=0.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.last_error = 0
        self.integral = 0

    def update(self, error, dt=0.033):
        self.integral += error * dt
        derivative = (error - self.last_error) / dt
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.last_error = error
        return output

# 사용
pid = PIDController(kp=0.5, ki=0.1, kd=0.05)
# 좌우 픽셀 수 차이를 에러로 사용
error = left_pixels - right_pixels
steering = pid.update(error)
```

---

## 📋 우선순위별 개선 사항

### 🔴 즉시 수정 (High Priority)
1. **배열 인덱싱 안전성** (207, 214번 줄)
2. **ROI 크기 검증** (149-151번 줄)
3. **시그널 핸들러 추가** (GPIO 안전성)

### 🟡 가능한 빨리 (Medium Priority)
4. **프레임 읽기 재시도 로직** (260-262번 줄)
5. **모터 제어 스무딩** (270-277번 줄)
6. **매직 넘버 상수화**

### 🟢 여유 있을 때 (Low Priority)
7. **성능 최적화** (색공간 변환, FPS 제한)
8. **로깅 시스템 추가**
9. **설정 저장/로드 기능**
10. **PID 제어 구현**

---

## 📝 개선된 코드 예시

```python
# 개선안 - decide_command 함수
def decide_command(frame, roi_height_ratio=0.3, roi_width_ratio=0.3,
                   thresh=150, min_pixels=100):
    """좌우 하단 ROI를 기반으로 제어 명령 결정"""
    h, w = frame.shape[:2]

    # ROI 크기 계산
    roi_h = int(h * roi_height_ratio)
    roi_w = int(w * roi_width_ratio)

    # 🔴 추가: 크기 검증
    if roi_h <= 0 or roi_w <= 0:
        logger.error(f"Invalid ROI size: h={roi_h}, w={roi_w}")
        return "stop", None, None, None, None, {"error": "invalid_roi"}

    roi_y = h - roi_h

    # ROI 추출
    left_roi = frame[roi_y:h, 0:roi_w]
    right_roi = frame[roi_y:h, w-roi_w:w]

    # 🔴 추가: 빈 ROI 검증
    if left_roi.size == 0 or right_roi.size == 0:
        logger.error("Empty ROI detected")
        return "stop", None, None, None, None, {"error": "empty_roi"}

    # 라인 감지
    left_has_line, left_pixels, left_binary = detect_line_in_roi(
        left_roi, thresh, min_pixels
    )
    right_has_line, right_pixels, right_binary = detect_line_in_roi(
        right_roi, thresh, min_pixels
    )

    # 제어 로직 (기존과 동일)
    if left_has_line and right_has_line:
        command = "forward"
    elif not left_has_line and right_has_line:
        command = "left"
    elif left_has_line and not right_has_line:
        command = "right"
    else:
        command = "stop"

    # 디버그 정보
    debug_info = {
        "left_has_line": left_has_line,
        "right_has_line": right_has_line,
        "left_pixels": left_pixels,
        "right_pixels": right_pixels,
        "roi_coords": {
            "left": (0, roi_y, roi_w, h),
            "right": (w-roi_w, roi_y, w, h)
        }
    }

    return command, left_roi, right_roi, left_binary, right_binary, debug_info
```

---

## 🎯 결론

### 현재 코드의 강점
- ✅ 깔끔한 구조와 우수한 가독성
- ✅ 실용적인 기능 (실시간 튜닝, 시각화)
- ✅ 플랫폼 독립성
- ✅ 좋은 문서화

### 개선이 필요한 핵심
- ⚠️ 에러 처리 강화
- ⚠️ 안전성 검증 추가
- ⚠️ 모터 제어 스무딩

### 추천 다음 단계
1. 즉시: 배열 인덱싱 안전성 수정
2. 단기: 에러 처리 개선
3. 중기: PID 제어 추가
4. 장기: 머신러닝 기반 라인 감지

---

**전체적으로 매우 잘 작성된 코드입니다!**
몇 가지 안전성 개선만 추가하면 프로덕션 레벨로 사용 가능합니다. 👍
