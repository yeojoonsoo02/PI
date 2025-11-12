"""
Line Tracer Integrated - 통합 라인 트레이서
교차로 감지 + 객체 인식 + 키보드 제어 통합 시스템

수정 사항 (2024-11-12):
- main() 함수명을 lane_follow_loop()으로 변경 (main.py와 연동)
- HSV 색상 범위 확장: [65, 20, 20] ~ [115, 255, 255]
- 픽셀 임계값 고정값 사용: 1200
- 라인 트레이싱 로직 단순화
"""
import cv2
import numpy as np
import time
import sys
import select
from gpiozero import DigitalOutputDevice, PWMOutputDevice
from collections import deque

# shared_state import 시도
try:
    import shared_state
    OBJECT_DETECTION_ENABLED = True
except ImportError:
    OBJECT_DETECTION_ENABLED = False
    print("[WARNING] shared_state not found. Object detection disabled.")

# ============================================================
# 표지판 인식 큐 시스템
# ============================================================
recognized_signs = deque(maxlen=5)  # 최근 5개 표지판만 저장
last_sign_time = 0  # 마지막 표지판 인식 시간
SIGN_COOLDOWN = 3.0  # 동일 표지판 재인식 방지 시간 (초)

# ============================================================
# 모터 / 부저 설정
# ============================================================
PWMA = PWMOutputDevice(18)
AIN1 = DigitalOutputDevice(22)
AIN2 = DigitalOutputDevice(27)

PWMB = PWMOutputDevice(23)
BIN1 = DigitalOutputDevice(25)
BIN2 = DigitalOutputDevice(24)

# 부저 설정
try:
    BUZZER = DigitalOutputDevice(12)
except Exception:
    BUZZER = None
    print("[WARNING] Buzzer not available")

# 속도 프로파일 (단순화 버전과 동일)
SPEED_FORWARD_DEFAULT = 0.75  # 기본 직진 속도
SPEED_TURN_DEFAULT = 0.55     # 기본 회전 속도
SPEED_SPIN_DEFAULT = 0.70     # 제자리 회전 속도
SPEED_SLOW_FORWARD = 0.25     # 감속 직진
SPEED_SLOW_TURN = 0.20         # 감속 회전

# 현재 속도 (동적 변경용)
SPEED_FORWARD = SPEED_FORWARD_DEFAULT
SPEED_TURN = SPEED_TURN_DEFAULT
SPEED_SPIN = SPEED_SPIN_DEFAULT

# ============================================================
# 모터 제어 함수
# ============================================================
def motor_forward():
    """전진"""
    AIN1.value = 0
    AIN2.value = 1
    PWMA.value = SPEED_FORWARD
    BIN1.value = 0
    BIN2.value = 1
    PWMB.value = SPEED_FORWARD

def motor_left(intensity=1.0):
    """좌회전 - intensity로 회전 강도 조절 (0.0~1.0)"""
    left_ratio = 0.25 * intensity
    right_ratio = 1.0 * intensity
    AIN1.value = 0
    AIN2.value = 1
    PWMA.value = SPEED_TURN * left_ratio
    BIN1.value = 0
    BIN2.value = 1
    PWMB.value = SPEED_TURN * right_ratio

def motor_right(intensity=1.0):
    """우회전 - intensity로 회전 강도 조절 (0.0~1.0)"""
    left_ratio = 1.0 * intensity
    right_ratio = 0.25 * intensity
    AIN1.value = 0
    AIN2.value = 1
    PWMA.value = SPEED_TURN * left_ratio
    BIN1.value = 0
    BIN2.value = 1
    PWMB.value = SPEED_TURN * right_ratio

def motor_spin_right():
    """제자리 우회전 (왼쪽 후진, 오른쪽 전진)"""
    AIN1.value = 1  # 왼쪽 후진
    AIN2.value = 0
    PWMA.value = SPEED_SPIN
    BIN1.value = 0  # 오른쪽 전진
    BIN2.value = 1
    PWMB.value = SPEED_SPIN

def motor_spin_left():
    """제자리 좌회전 (왼쪽 전진, 오른쪽 후진)"""
    AIN1.value = 0  # 왼쪽 전진
    AIN2.value = 1
    PWMA.value = SPEED_SPIN
    BIN1.value = 1  # 오른쪽 후진
    BIN2.value = 0
    PWMB.value = SPEED_SPIN

def motor_stop():
    """정지 - 완전한 브레이크 모드"""
    AIN1.value = 0
    AIN2.value = 0  # 왼쪽 모터 브레이크
    PWMA.value = 0.0
    BIN1.value = 0
    BIN2.value = 0  # 오른쪽 모터 브레이크
    PWMB.value = 0.0

def set_slow_mode():
    """감속 모드 설정"""
    global SPEED_FORWARD, SPEED_TURN
    SPEED_FORWARD = SPEED_SLOW_FORWARD
    SPEED_TURN = SPEED_SLOW_TURN
    print("  [속도] 감속 모드 활성화")

def restore_speed():
    """정상 속도 복원"""
    global SPEED_FORWARD, SPEED_TURN
    SPEED_FORWARD = SPEED_FORWARD_DEFAULT
    SPEED_TURN = SPEED_TURN_DEFAULT
    print("  [속도] 정상 속도 복원")

def beep(sec=1.0):
    """부저 울리기"""
    if BUZZER:
        BUZZER.value = 1
        time.sleep(sec)
        BUZZER.value = 0
    else:
        print("🔊 (buzzer simulated)")
        time.sleep(sec)

# ============================================================
# 유틸리티 함수
# ============================================================
def get_user_input():
    """사용자 입력 확인 (non-blocking)"""
    if select.select([sys.stdin], [], [], 0)[0]:
        try:
            key = sys.stdin.read(1).lower()
            return key
        except:
            return None
    return None

# ============================================================
# 객체 인식 트리거 처리 (shared_state 기반)
# ============================================================
def handle_runtime_triggers(frame_count=0):
    """주행 중 객체 인식 트리거 처리"""
    if not OBJECT_DETECTION_ENABLED:
        return False

    handled = False
    timestamp = time.strftime("%H:%M:%S")

    with shared_state.lock:
        obj_state = shared_state.object_state.copy()
        trig = shared_state.last_trigger
        # 신뢰도 정보가 있으면 가져오기
        confidence = getattr(shared_state, 'confidence', {})

    # 객체 상태 확인 및 알림
    if any(obj_state.values()):
        detected_objects = [k for k, v in obj_state.items() if v]
        if detected_objects:
            # 새로운 객체 감지 시 즉시 알림
            for obj in detected_objects:
                show_notification = False
                try:
                    if not getattr(shared_state, f'{obj}_notified', False):
                        show_notification = True
                        with shared_state.lock:
                            setattr(shared_state, f'{obj}_notified', True)
                except:
                    # shared_state에서 notified 플래그 관리가 안 되는 경우에도 알림 표시
                    show_notification = True

                if show_notification:
                    # 객체별 명확한 알림
                    obj_names = {
                        'stop': '🛑 STOP 표지판',
                        'slow': '⚠️ SLOW 표지판',
                        'horn': '📢 HORN 표지판',
                        'traffic': '🚦 신호등',
                        'go_straight': '⬆️ 직진 표지판',
                        'turn_left': '⬅️ 좌회전 표지판',
                        'turn_right': '➡️ 우회전 표지판'
                    }
                    obj_display = obj_names.get(obj, obj.upper())
                    conf = confidence.get(obj, 0) if confidence else 0

                    print(f"\n{'='*50}")
                    print(f"🎯 객체 감지 알림!")
                    print(f"  감지된 객체: {obj_display}")
                    if conf > 0:
                        print(f"  신뢰도: {conf:.1%}")
                    print(f"  시간: {timestamp}")
                    print(f"  프레임: #{frame_count}")
                    print(f"{'='*50}\n")

            # 주기적 상태 로깅 (10프레임마다)
            if frame_count % 10 == 0:
                conf_str = ""
                if confidence:
                    conf_values = [f"{k}:{confidence.get(k, 0):.2f}" for k in detected_objects if k in confidence]
                    if conf_values:
                        conf_str = f" [신뢰도: {', '.join(conf_values)}]"
                print(f"  [객체 상태] {timestamp} F#{frame_count} | 감지: {', '.join(detected_objects)}{conf_str}")
    else:
        # 객체가 사라지면 알림 플래그 리셋
        try:
            with shared_state.lock:
                for attr in dir(shared_state):
                    if attr.endswith('_notified'):
                        delattr(shared_state, attr)
        except:
            pass  # 플래그 리셋 실패는 무시

    # STOP 표지판
    if obj_state.get("stop"):
        conf = confidence.get("stop", 0) if confidence else 0
        print(f"🛑 [객체인식] STOP 표지판 감지 → 3초 정지")
        print(f"  └─ {timestamp} | Frame #{frame_count} | 신뢰도: {conf:.2f}" if conf else f"  └─ {timestamp} | Frame #{frame_count}")
        motor_stop()
        time.sleep(3)
        print(f"  └─ STOP 동작 완료 ({timestamp})")
        handled = True

    # SLOW 표지판
    elif obj_state.get("slow"):
        conf = confidence.get("slow", 0) if confidence else 0
        print(f"⚠️ [객체인식] SLOW 표지판 감지 → 3초 감속")
        print(f"  └─ {timestamp} | Frame #{frame_count} | 신뢰도: {conf:.2f}" if conf else f"  └─ {timestamp} | Frame #{frame_count}")
        set_slow_mode()
        motor_forward()
        time.sleep(3)
        restore_speed()
        print(f"  └─ SLOW 동작 완료 ({timestamp})")
        handled = True

    # HORN 표지판
    elif obj_state.get("horn"):
        conf = confidence.get("horn", 0) if confidence else 0
        print(f"📢 [객체인식] HORN 표지판 감지 → 경적 1초")
        print(f"  └─ {timestamp} | Frame #{frame_count} | 신뢰도: {conf:.2f}" if conf else f"  └─ {timestamp} | Frame #{frame_count}")
        beep(1.0)
        print(f"  └─ HORN 동작 완료 ({timestamp})")
        handled = True

    # 신호등 (traffic)
    elif obj_state.get("traffic"):
        conf = confidence.get("traffic", 0) if confidence else 0
        print(f"🚦 [객체인식] 신호등 감지 → 3초 정지 후 우회전")
        print(f"  └─ {timestamp} | Frame #{frame_count} | 신뢰도: {conf:.2f}" if conf else f"  └─ {timestamp} | Frame #{frame_count}")
        motor_stop()
        time.sleep(3)
        motor_right()
        time.sleep(0.8)
        motor_forward()
        time.sleep(0.5)
        with shared_state.lock:
            shared_state.right_turn_done = True
        print(f"  └─ 신호등 우회전 완료 ({timestamp})")
        handled = True

    if handled:
        with shared_state.lock:
            shared_state.last_trigger = None
        print(f"  └─ 트리거 처리 완료 및 초기화 ({timestamp})")

    return handled

def try_branch_by_trigger(frame_count=0):
    """교차로에서 저장된 방향 표지판 실행"""
    # 저장된 표지판이 있으면 실행
    if execute_stored_sign():
        print(f"  [교차로] 저장된 표지판 실행 완료")
        return True
    return False

# ============================================================
# 카메라 초기화
# ============================================================
def init_camera():
    """카메라 초기화 - 640x480 해상도"""
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            from picamera2 import Picamera2
            print(f"[INFO] Initializing camera... (Attempt {attempt + 1}/{max_retries})")

            # 카메라가 사용 중일 수 있으므로 잠시 대기
            if attempt > 0:
                print(f"[INFO] Waiting {retry_delay} seconds...")
                time.sleep(retry_delay)

                # 카메라 관련 프로세스 종료 시도
                import subprocess
                subprocess.run(['pkill', '-f', 'libcamera'], capture_output=True)
                time.sleep(0.5)

            picam2 = Picamera2()
            config = picam2.create_preview_configuration(
                main={"format": "RGB888", "size": (640, 480)}
            )
            picam2.configure(config)
            picam2.start()
            time.sleep(2)

            print("[✓] Camera ready (640x480)")

            class CameraWrapper:
                def read(self):
                    frame = picam2.capture_array()
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    return True, frame

                def release(self):
                    picam2.stop()

            return CameraWrapper()

        except Exception as e:
            print(f"[ERROR] Camera failed: {e}")

            if "Pipeline handler in use" in str(e):
                print("[INFO] Camera is in use by another process.")
                if attempt < max_retries - 1:
                    print("[INFO] Attempting to free camera...")
                else:
                    print("\n[ERROR] Failed to initialize camera after all retries.")
                    print("\n해결 방법:")
                    print("1. 터미널에서 실행:")
                    print("   sudo pkill -9 python")
                    print("2. 1초 후 다시 실행:")
                    print("   python " + sys.argv[0])

    return None

# ============================================================
# 표지판 관리 함수
# ============================================================
def store_direction_signs(frame_count=0):
    """방향 표지판을 인식하여 큐에 저장만 함"""
    if not OBJECT_DETECTION_ENABLED:
        return

    global last_sign_time
    current_time = time.time()

    # 쿨다운 체크
    if current_time - last_sign_time < SIGN_COOLDOWN:
        return

    with shared_state.lock:
        obj_state = shared_state.object_state.copy()
        confidence = getattr(shared_state, 'confidence', {})

    timestamp = time.strftime("%H:%M:%S")
    direction_signs = ["go_straight", "turn_left", "turn_right"]

    for sign in direction_signs:
        if obj_state.get(sign):
            conf = confidence.get(sign, 0) if confidence else 0
            sign_info = {
                'type': sign,
                'confidence': conf,
                'time': current_time,
                'timestamp': timestamp,
                'frame': frame_count
            }

            # 큐에 저장 (중복 방지)
            if not recognized_signs or recognized_signs[-1]['type'] != sign:
                recognized_signs.append(sign_info)
                last_sign_time = current_time

                # 인식 로그만 출력
                if sign == "go_straight":
                    print(f"⬆️ [표지판 인식] 직진 표지판 감지 (저장됨)")
                elif sign == "turn_left":
                    print(f"⬅️ [표지판 인식] 좌회전 표지판 감지 (저장됨)")
                elif sign == "turn_right":
                    print(f"➡️ [표지판 인식] 우회전 표지판 감지 (저장됨)")

                print(f"  └─ {timestamp} | Frame #{frame_count} | 신뢰도: {conf:.2f}")
                print(f"  └─ 큐에 {len(recognized_signs)}개 표지판 저장됨")
                break  # 한 번에 하나만 저장

def execute_stored_sign():
    """저장된 표지판을 실행 (교차로나 정지 시)"""
    if not recognized_signs:
        return False

    # 가장 최근 표지판 가져오기
    sign_info = recognized_signs.popleft()
    sign_type = sign_info['type']
    timestamp = sign_info['timestamp']
    conf = sign_info['confidence']

    print(f"\n{'='*50}")
    print(f"📋 저장된 표지판 실행")
    print(f"{'='*50}")

    if sign_type == "go_straight":
        print(f"⬆️ 직진 표지판 → 직진 실행")
        print(f"  └─ 저장시간: {timestamp} | 신뢰도: {conf:.2f}")
        motor_stop()
        time.sleep(0.5)
        motor_forward()
        time.sleep(1.5)
        print(f"  └─ 직진 완료")
        return True

    elif sign_type == "turn_left":
        print(f"⬅️ 좌회전 표지판 → 좌회전 실행")
        print(f"  └─ 저장시간: {timestamp} | 신뢰도: {conf:.2f}")
        motor_stop()
        time.sleep(0.5)
        motor_forward()
        time.sleep(0.5)  # 코너 접근
        motor_left(1.0)
        time.sleep(1.5)  # 회전 시간
        motor_forward()
        time.sleep(0.5)  # 라인 복귀
        print(f"  └─ 좌회전 완료")
        return True

    elif sign_type == "turn_right":
        print(f"➡️ 우회전 표지판 → 우회전 실행")
        print(f"  └─ 저장시간: {timestamp} | 신뢰도: {conf:.2f}")
        motor_stop()
        time.sleep(0.5)
        motor_forward()
        time.sleep(0.5)  # 코너 접근
        motor_right(1.0)
        time.sleep(1.5)  # 회전 시간
        motor_forward()
        time.sleep(0.5)  # 라인 복귀
        print(f"  └─ 우회전 완료")
        return True

    return False

# ============================================================
# 균형 바 생성
# ============================================================
def create_balance_bar(left_ratio, right_ratio):
    """좌우 균형 시각화 바 생성"""
    bar_length = 20

    if left_ratio == 0 and right_ratio == 0:
        return "[" + " " * bar_length + "]"

    left_bars = int(left_ratio * bar_length)
    right_bars = int(right_ratio * bar_length)

    bar = "L[" + "█" * left_bars + " " * (bar_length - left_bars) + "|" + \
          "█" * right_bars + " " * (bar_length - right_bars) + "]R"

    return bar

# ============================================================
# 메인 루프
# ============================================================
def lane_follow_loop():
    """통합 라인 트레이서 메인 루프"""
    print("=" * 70)
    print(" Line Tracer Integrated - 통합 라인 트레이서")
    print("=" * 70)
    print()
    print("기능:")
    print("  • 교차로 자동 감지 및 정지")
    print("  • 객체 인식 트리거 (표지판, 신호등)")
    print("  • 키보드 수동 제어")
    print("  • 부저 경적")
    print()
    print("교차로 감지 시:")
    print("  → 자동 정지 후 선택 대기")
    print("  [a] 좌회전 | [d] 우회전 | [w] 직진 | [s] 정지")
    print()
    print("객체 인식: " + ("활성화" if OBJECT_DETECTION_ENABLED else "비활성화"))

    if OBJECT_DETECTION_ENABLED:
        print("  ├─ STOP, SLOW, HORN 표지판 감지")
        print("  ├─ 신호등 감지 및 자동 우회전")
        print("  ├─ 교차로 방향 표지판 (직진/좌회전/우회전)")
        print("  └─ 실시간 신뢰도 및 프레임 로깅")

        # shared_state 초기 상태 확인
        try:
            with shared_state.lock:
                initial_state = shared_state.object_state.copy()
            print(f"  [객체탐지 시스템] 초기화 완료 - shared_state 연결 성공")
        except Exception as e:
            print(f"  [객체탐지 시스템] 경고: shared_state 접근 오류: {e}")
    else:
        print("  └─ shared_state 모듈 없음 - 객체 인식 비활성화")

    print()
    print("[INFO] Press Ctrl+C to stop")
    print()

    camera = init_camera()
    if not camera:
        return

    # HSV 범위 - 청록색(Cyan) 라인용 (확장된 범위)
    lower_cyan = np.array([65, 20, 20])
    upper_cyan = np.array([115, 255, 255])

    start_time = time.time()
    frame_count = 0
    action_stats = {"FORWARD": 0, "LEFT": 0, "RIGHT": 0, "STOP": 0, "INTERSECTION": 0}

    # 현재 동작 상태 초기화 (오류 수정)
    action = "STOP"

    # 균형 임계값 (직진 판단)
    BALANCE_THRESHOLD = 0.30  # 좌우 균형 차이가 이 값 이하면 직진

    # 박스 크기 설정 (해상도에 맞춰)
    BOX_WIDTH_RATIO = 0.25   # 화면 너비의 25%
    BOX_HEIGHT_RATIO = 0.25  # 화면 높이의 25%

    # 박스 크기 초기화 (640x480 기준)
    width = 640
    height = 480
    BOX_WIDTH = int(width * BOX_WIDTH_RATIO)
    BOX_HEIGHT = int(height * BOX_HEIGHT_RATIO)

    # 픽셀 임계값 (고정값)
    PIXEL_THRESHOLD = 800  # 라인 감지 임계값 (더 민감하게 조정)
    CENTER_THRESHOLD = 5000  # 교차로 감지 임계값 (고정)

    # 회전 강도 임계값
    TURN_THRESHOLD_STRONG = 0.6   # 강한 회전
    TURN_THRESHOLD_MEDIUM = 0.4   # 중간 회전

    # 라인 탐색 방향 (라인을 잃었을 때 마지막으로 본 방향)
    # last_seen_side = None  # 현재 미사용

    # 교차로 모드 관련 변수
    intersection_mode = False
    intersection_exit_time = None
    INTERSECTION_EXIT_DURATION = 2.0

    # 라인 손실 관련
    line_lost_time = None

    # 차량 상태 관련
    vehicle_stopped = False  # 차량 정지 상태
    stop_reason = None  # 정지 이유

    try:
        while True:
            ret, frame = camera.read()
            if not ret:
                print("[ERROR] Failed to read frame")
                break

            frame_count += 1

            # 이미지 뒤집기
            frame = cv2.flip(frame, -1)

            # 전체 프레임 크기
            height, width = frame.shape[:2]

            # ====== 차량 정지 상태 판단 ======
            # 교차로 모드일 때만 vehicle_stopped 사용
            if intersection_mode:
                if not vehicle_stopped:
                    vehicle_stopped = True
                    stop_reason = "교차로 대기"
            else:
                if vehicle_stopped and stop_reason == "교차로 대기":
                    vehicle_stopped = False
                    stop_reason = None

            # shared_state에 프레임 전달 (객체 인식용) - 정지 중에도 객체 인식은 계속
            if OBJECT_DETECTION_ENABLED and frame_count % 3 == 0:
                try:
                    with shared_state.lock:
                        shared_state.latest_frame = frame.copy()
                        # 차량 주행 중일 때만 로깅
                        if not vehicle_stopped and frame_count % 30 == 0:
                            # 객체 인식 모듈 상태 체크 (옵션)
                            obj_module_active = getattr(shared_state, 'detector_active', False)
                            if obj_module_active:
                                print(f"  [객체탐지] Frame #{frame_count} → shared_state 전송 (감지기 활성)")
                            else:
                                print(f"  [객체탐지] Frame #{frame_count} → shared_state 전송")
                except Exception as e:
                    if not vehicle_stopped and frame_count % 30 == 0:
                        print(f"  [객체탐지 오류] Frame #{frame_count} 전송 실패: {e}")

            # ====== 방향 표지판을 큐에 저장 (주행 중에도 계속 인식) ======
            if OBJECT_DETECTION_ENABLED and frame_count % 5 == 0:
                store_direction_signs(frame_count)

            # ====== 교차로에서만 특별 처리 ======
            if vehicle_stopped and stop_reason == "교차로 대기":
                # 교차로에서는 라인 인식 건너뛰기
                left_pixels = 0
                right_pixels = 0
                center_pixels = 0
                total_pixels = 0
                left_ratio = 0.0
                right_ratio = 0.0
                diff = 0.0

                # 박스 크기 계산
                BOX_WIDTH = int(width * BOX_WIDTH_RATIO)
                BOX_HEIGHT = int(height * BOX_HEIGHT_RATIO)

            else:
                # ====== 정상 주행 - 라인 인식 수행 ======
                # 동적 박스 크기 계산
                BOX_WIDTH = int(width * BOX_WIDTH_RATIO)
                BOX_HEIGHT = int(height * BOX_HEIGHT_RATIO)

                # PIXEL_THRESHOLD는 이미 고정값으로 설정됨 (1200)

                # 좌하단 박스
                left_box_x1 = 0
                left_box_y1 = height - BOX_HEIGHT
                left_box_x2 = BOX_WIDTH
                left_box_y2 = height
                left_box = frame[left_box_y1:left_box_y2, left_box_x1:left_box_x2]

                # 우하단 박스
                right_box_x1 = width - BOX_WIDTH
                right_box_y1 = height - BOX_HEIGHT
                right_box_x2 = width
                right_box_y2 = height
                right_box = frame[right_box_y1:right_box_y2, right_box_x1:right_box_x2]

                # 전방 중앙 박스 (교차로 감지용)
                center_box_width = int(width * 0.6)  # 화면 너비의 60%
                center_box_height = int(height * 0.15)  # 화면 높이의 15%
                center_box_x1 = (width - center_box_width) // 2
                center_box_y1 = int(height * 0.3)  # 화면 상단 30% 위치
                center_box_x2 = center_box_x1 + center_box_width
                center_box_y2 = center_box_y1 + center_box_height
                center_box = frame[center_box_y1:center_box_y2, center_box_x1:center_box_x2]

                # 좌측 박스 처리
                hsv_left = cv2.cvtColor(left_box, cv2.COLOR_BGR2HSV)
                mask_left = cv2.inRange(hsv_left, lower_cyan, upper_cyan)

                # 노이즈 제거
                kernel = np.ones((3, 3), np.uint8)
                mask_left = cv2.erode(mask_left, kernel, iterations=2)
                mask_left = cv2.dilate(mask_left, kernel, iterations=3)

                # 우측 박스 처리
                hsv_right = cv2.cvtColor(right_box, cv2.COLOR_BGR2HSV)
                mask_right = cv2.inRange(hsv_right, lower_cyan, upper_cyan)
                mask_right = cv2.erode(mask_right, kernel, iterations=2)
                mask_right = cv2.dilate(mask_right, kernel, iterations=3)

                # 전방 중앙 박스 처리 (교차로 감지)
                hsv_center = cv2.cvtColor(center_box, cv2.COLOR_BGR2HSV)
                mask_center = cv2.inRange(hsv_center, lower_cyan, upper_cyan)
                mask_center = cv2.erode(mask_center, kernel, iterations=2)
                mask_center = cv2.dilate(mask_center, kernel, iterations=3)

                # 픽셀 수 계산
                left_pixels = cv2.countNonZero(mask_left)
                right_pixels = cv2.countNonZero(mask_right)
                center_pixels = cv2.countNonZero(mask_center)
                total_pixels = left_pixels + right_pixels

                # CENTER_THRESHOLD는 이미 고정값으로 설정됨 (5000)

                # 좌우 비율 계산
                if total_pixels > 0:
                    left_ratio = left_pixels / total_pixels
                    right_ratio = right_pixels / total_pixels
                else:
                    left_ratio = 0.0
                    right_ratio = 0.0

                # 좌우 차이
                diff = abs(left_ratio - right_ratio)

            # 균형 임계값은 고정값 사용 (BALANCE_THRESHOLD)

            # 조향 결정
            action = "STOP"


            # ====== 교차로 모드에서 키보드 입력 처리 ======
            if intersection_mode:
                # 먼저 저장된 표지판 확인하여 실행
                if OBJECT_DETECTION_ENABLED and try_branch_by_trigger(frame_count):
                    print("  [교차로] 저장된 표지판 → 자동 실행")
                    intersection_mode = False
                    intersection_exit_time = time.time()
                    line_lost_time = None
                    vehicle_stopped = False
                    continue

                # 키보드 입력 확인
                user_input = get_user_input()
                if user_input:
                    print(f"\n[교차로] 선택: {user_input}")

                    if user_input == 'w':
                        motor_forward()
                        action = "FORWARD"
                        print("  → 직진 선택")
                        intersection_mode = False
                        intersection_exit_time = time.time()
                        vehicle_stopped = False
                    elif user_input == 'a':
                        print("  → 좌회전 선택 (직진 0.5초 후 회전 1.2초)")
                        motor_forward()
                        time.sleep(0.5)  # 직진으로 접근
                        motor_left(1.0)
                        time.sleep(1.2)  # 회전 시간 (기존보다 길게)
                        action = "LEFT"
                        intersection_mode = False
                        intersection_exit_time = time.time()
                        vehicle_stopped = False
                    elif user_input == 'd':
                        print("  → 우회전 선택 (직진 0.5초 후 회전 1.2초)")
                        motor_forward()
                        time.sleep(0.5)  # 직진으로 접근
                        motor_right(1.0)
                        time.sleep(1.2)  # 회전 시간 (기존보다 길게)
                        action = "RIGHT"
                        intersection_mode = False
                        intersection_exit_time = time.time()
                        vehicle_stopped = False
                    elif user_input == 's':
                        motor_stop()
                        action = "STOP"
                        print("  → 정지 유지")
                else:
                    # 키보드 입력 대기 중
                    motor_stop()
                    action = "INTERSECTION"
                continue

            # ====== 교차로 탈출 중이면 일정 시간 교차로 감지 무시 ======
            if intersection_exit_time:
                elapsed = time.time() - intersection_exit_time
                if elapsed < INTERSECTION_EXIT_DURATION:
                    # 교차로 탈출 중 - 이전 동작 유지
                    pass
                else:
                    # 탈출 완료
                    intersection_exit_time = None

            # ====== 교차로 감지 (전방에 수평선이 있고 좌우 픽셀이 적을 때) ======
            elif not intersection_exit_time and center_pixels > CENTER_THRESHOLD and total_pixels < PIXEL_THRESHOLD * 2:
                if not intersection_mode:
                    motor_stop()
                    action = "INTERSECTION"
                    intersection_mode = True
                    print(f"\n🛑 교차로 감지! 전방:{center_pixels} 좌우:{total_pixels}")
                    if OBJECT_DETECTION_ENABLED:
                        print("  표지판 인식 대기 중...")
                    print("  [a] 좌회전 | [d] 우회전 | [w] 직진 | [s] 정지")
                    print("  선택 대기 중...")

            # ====== 라인이 거의 안 보일 때 (교차로가 아닌 경우) ======
            elif total_pixels < PIXEL_THRESHOLD:
                # 최초 라인 이탈 시에만 정지하고 메시지 출력
                if line_lost_time is None:
                    line_lost_time = time.time()
                    motor_stop()
                    action = "STOP"
                    print(f"\n⚠️ 라인 이탈! 수동 제어 가능")
                    print("  [w] 직진 | [a] 좌회전 | [d] 우회전 | [s] 정지")

                # 키보드 입력 확인
                user_input = get_user_input()
                if user_input:
                    if user_input == 'w':
                        motor_forward()
                        action = "FORWARD"
                        print("  → 직진 실행")
                    elif user_input == 'a':
                        print("  → 좌회전 실행 (직진 0.5초 후 회전 1.2초)")
                        motor_forward()
                        time.sleep(0.5)  # 직진으로 접근
                        motor_left(1.0)
                        time.sleep(1.2)  # 회전 시간 (기존보다 길게)
                        action = "LEFT"
                    elif user_input == 'd':
                        print("  → 우회전 실행 (직진 0.5초 후 회전 1.2초)")
                        motor_forward()
                        time.sleep(0.5)  # 직진으로 접근
                        motor_right(1.0)
                        time.sleep(1.2)  # 회전 시간 (기존보다 길게)
                        action = "RIGHT"
                    elif user_input == 's':
                        motor_stop()
                        action = "STOP"
                        print("  → 정지")
                # 입력이 없으면 현재 동작 유지

            # ====== 라인이 충분히 보일 때 조향 제어 ======
            elif total_pixels >= PIXEL_THRESHOLD:
                # 라인 복귀 알림
                if line_lost_time is not None:
                    print("✓ 라인 복귀 → 자동 주행 모드")
                    line_lost_time = None

                vehicle_stopped = False  # 라인 찾으면 정지 상태 해제

                if diff < BALANCE_THRESHOLD:
                    # 좌우 균형 잡힘 → 전진
                    motor_forward()
                    action = "FORWARD"

                elif left_pixels > right_pixels:
                    # 왼쪽에 청록색이 많음 → 우회전 필요
                    # 편차가 크면 강한 회전, 작으면 약한 회전
                    if diff > TURN_THRESHOLD_STRONG:  # 큰 편차 - 강한 회전
                        motor_right(1.0)
                    elif diff > TURN_THRESHOLD_MEDIUM:  # 중간 편차 - 중간 회전
                        motor_right(0.7)
                    else:  # 작은 편차 - 약한 회전
                        motor_right(0.5)
                    action = "RIGHT"

                else:
                    # 오른쪽에 청록색이 많음 → 좌회전 필요
                    # 편차가 크면 강한 회전, 작으면 약한 회전
                    if diff > TURN_THRESHOLD_STRONG:  # 큰 편차 - 강한 회전
                        motor_left(1.0)
                    elif diff > TURN_THRESHOLD_MEDIUM:  # 중간 편차 - 중간 회전
                        motor_left(0.7)
                    else:  # 작은 편차 - 약한 회전
                        motor_left(0.5)
                    action = "LEFT"

                # 주행 중 객체 인식 트리거 처리
                handle_runtime_triggers(frame_count)

            # 통계 업데이트
            action_stats[action] += 1

            # 로그 출력 (10프레임마다) - 정지 상태일 때는 건너뛰기
            if frame_count % 10 == 0 and not vehicle_stopped:
                runtime = int(time.time() - start_time)

                # 상태 아이콘
                icons = {
                    "FORWARD": "↑",
                    "LEFT": "←",
                    "RIGHT": "→",
                    "INTERSECTION": "🛑",
                    "STOP": "■"
                }
                icon = icons.get(action, "?")

                # 균형 상태 표시
                balance_bar = create_balance_bar(left_ratio, right_ratio)

                # 로그 출력
                print(f"[{runtime:3d}s] F:{frame_count:5d} | "
                      f"L:{left_pixels:4d} R:{right_pixels:4d} C:{center_pixels:4d} | "
                      f"{balance_bar} | "
                      f"D:{diff:.2f} | {icon} {action:11s}")

            time.sleep(0.02)  # 더 빠른 반응

    except KeyboardInterrupt:
        print("\n\n[INFO] Stopped by user")

    finally:
        runtime = int(time.time() - start_time)
        print()
        print("=" * 70)
        print(" Session Summary")
        print("=" * 70)
        print(f"Runtime        : {runtime}s")
        print(f"Total frames   : {frame_count}")
        print(f"Average FPS    : {frame_count/max(runtime, 1):.1f}")
        print()
        print("Actions:")
        for action in ["FORWARD", "LEFT", "RIGHT", "INTERSECTION", "STOP"]:
            count = action_stats.get(action, 0)
            percentage = (count / max(frame_count, 1)) * 100
            bar = "█" * int(percentage / 2)
            print(f"  {action:12s} : {count:5d} ({percentage:5.1f}%) {bar}")
        print()

        # 성능 분석
        forward_ratio = action_stats["FORWARD"] / max(frame_count, 1)
        intersection_ratio = action_stats.get("INTERSECTION", 0) / max(frame_count, 1)
        stop_ratio = action_stats["STOP"] / max(frame_count, 1)

        if intersection_ratio > 0.1:
            print("✓ 교차로 감지 성공!")
            print(f"  → 교차로 감지 비율: {intersection_ratio*100:.1f}%")
        elif stop_ratio > 0.7:
            print("✗ 청록색 감지 실패 (대부분 정지)")
            print("  → HSV 범위 조정 필요")
        elif forward_ratio > 0.5:
            print("✓ 좋은 성능 (직진 비율 높음)")
        elif forward_ratio > 0.3:
            print("⚠ 보통 성능 (회전이 많음)")
        else:
            print("⚠ 불안정한 주행 (회전 과다)")

        print()
        print("사용된 설정:")
        print(f"  해상도: {width}x{height}")
        print(f"  박스 크기: {BOX_WIDTH}x{BOX_HEIGHT}")
        print(f"  픽셀 임계값: {PIXEL_THRESHOLD}")
        print(f"  균형 임계값: {BALANCE_THRESHOLD:.2f}")
        print(f"  객체 인식: {'활성화' if OBJECT_DETECTION_ENABLED else '비활성화'}")

        # 객체 인식 통계 (활성화된 경우)
        if OBJECT_DETECTION_ENABLED:
            print()
            print("객체 인식 통계:")
            try:
                with shared_state.lock:
                    obj_counts = getattr(shared_state, 'detection_counts', {})

                if obj_counts:
                    for obj_type, count in obj_counts.items():
                        print(f"  {obj_type}: {count}회 감지")
                else:
                    print("  객체 감지 횟수 기록 없음")
                print("  ※ 자세한 로그는 실행 중 콘솔 출력 참조")
            except:
                print("  객체 감지 통계 접근 실패")

        print("=" * 70)

        # 모터 완전 정지
        motor_stop()
        PWMA.value = 0.0
        PWMB.value = 0.0
        camera.release()
        print("[✓] Cleanup complete")

if __name__ == '__main__':
    lane_follow_loop()