"""
lane_tracer.py (단순화 버전)
---------------------------
Line Tracing + Object Trigger (통합 시스템)
 - shared_state의 상태맵 기반으로 동작
"""

import cv2
import numpy as np
import time
import sys
import select
from gpiozero import DigitalOutputDevice, PWMOutputDevice
import shared_state


# ============================================================
# 모터 / 부저 설정
# ============================================================

PWMA = PWMOutputDevice(18)
AIN1 = DigitalOutputDevice(22)
AIN2 = DigitalOutputDevice(27)

PWMB = PWMOutputDevice(23)
BIN1 = DigitalOutputDevice(25)
BIN2 = DigitalOutputDevice(24)

# 부저 
try:
    BUZZER = DigitalOutputDevice(12)
except Exception:
    BUZZER = None


# 기본/감속 속도 프로파일
SPEED_FORWARD_DEFAULT = 0.75
SPEED_TURN_DEFAULT    = 0.55
SPEED_SLOW_FORWARD    = 0.25
SPEED_SLOW_TURN       = 0.20

SPEED_FORWARD = SPEED_FORWARD_DEFAULT
SPEED_TURN    = SPEED_TURN_DEFAULT


# ============================================================
# 모터 제어 함수
# ============================================================

def motor_forward():
    AIN1.value = 0; AIN2.value = 1
    PWMA.value = SPEED_FORWARD
    BIN1.value = 0; BIN2.value = 1
    PWMB.value = SPEED_FORWARD

def motor_left(intensity=1.0):
    """좌회전 - intensity로 회전 강도 조절 (0.0~1.0)"""
    left_ratio = 0.25 * intensity
    right_ratio = 1.0 * intensity
    AIN1.value = 0; AIN2.value = 1
    PWMA.value = SPEED_TURN * left_ratio
    BIN1.value = 0; BIN2.value = 1
    PWMB.value = SPEED_TURN * right_ratio

def motor_right(intensity=1.0):
    """우회전 - intensity로 회전 강도 조절 (0.0~1.0)"""
    left_ratio = 1.0 * intensity
    right_ratio = 0.25 * intensity
    AIN1.value = 0; AIN2.value = 1
    PWMA.value = SPEED_TURN * left_ratio
    BIN1.value = 0; BIN2.value = 1
    PWMB.value = SPEED_TURN * right_ratio

def motor_stop():
    # 두 모터 모두 정지 (방향 일치)
    AIN1.value = 0; AIN2.value = 0  # 왼쪽 모터 완전 정지
    PWMA.value = 0.0
    BIN1.value = 0; BIN2.value = 0  # 오른쪽 모터 완전 정지
    PWMB.value = 0.0

def set_slow_mode():
    global SPEED_FORWARD, SPEED_TURN
    SPEED_FORWARD = SPEED_SLOW_FORWARD
    SPEED_TURN    = SPEED_SLOW_TURN

def restore_speed():
    global SPEED_FORWARD, SPEED_TURN
    SPEED_FORWARD = SPEED_FORWARD_DEFAULT
    SPEED_TURN    = SPEED_TURN_DEFAULT

def beep(sec=1.0):
    if BUZZER:
        BUZZER.value = 1
        time.sleep(sec)
        BUZZER.value = 0
    else:
        print("🔊 (buzzer simulated)")
        time.sleep(sec)


# ============================================================
# 유틸리티
# ============================================================

def get_user_input():
    """사용자 입력 확인 (non-blocking)"""
    if select.select([sys.stdin], [], [], 0)[0]:
        try:
            return sys.stdin.read(1).lower()
        except:
            return None
    return None


# ============================================================
# 객체 트리거 처리
# ============================================================

def handle_runtime_triggers():
    """
    CRUISE 주행 중 수시로 호출.
    stop, slow, horn, traffic 처리.
    """
    handled = False

    with shared_state.lock:
        obj_state = shared_state.object_state.copy()
        trig = shared_state.last_trigger

    # stop
    if obj_state.get("stop"):
        print("STOP sign → 정지 3초")
        motor_stop(); time.sleep(3)
        handled = True

    # slow
    elif obj_state.get("slow"):
        print("SLOW sign → 감속 3초")
        set_slow_mode(); motor_forward()
        time.sleep(3); restore_speed()
        handled = True

    # horn
    elif obj_state.get("horn"):
        print("HORN sign → 경적 1초")
        beep(1.0)
        handled = True

    # traffic (항상 초록불 → 정지 후 우회전)
    elif obj_state.get("traffic"):
        print("TRAFFIC light detected → 3초 정지 후 우회전")
        motor_stop(); time.sleep(3)
        motor_right(); time.sleep(0.8)
        motor_forward(); time.sleep(0.5)
        with shared_state.lock:
            shared_state.right_turn_done = True
        handled = True

    if handled:
        with shared_state.lock:
            shared_state.last_trigger = None
    return handled


def try_branch_by_trigger():
    """
    교차로 등에서 go_straight / turn_left / turn_right 수행
    """
    acted = False
    with shared_state.lock:
        obj_state = shared_state.object_state.copy()

    if obj_state.get("go_straight"):
        print("^ go_straight 인식 → 직진")
        motor_stop(); time.sleep(1)
        motor_forward(); time.sleep(1.5)
        acted = True

    elif obj_state.get("turn_left"):
        print("↩ turn_left 인식 → 좌회전")
        motor_stop(); time.sleep(0.5)
        motor_forward(); time.sleep(0.5)     # 코너 접근
        motor_left(); time.sleep(1.0)        # 회전 진입
        motor_forward(); time.sleep(0.5)     # 라인 복귀
        acted = True

    elif obj_state.get("turn_right"):
        print("↪ turn_right 인식 → 우회전")
        motor_stop(); time.sleep(0.5)
        motor_forward(); time.sleep(0.5)
        motor_right(); time.sleep(1.0)
        motor_forward(); time.sleep(0.5)
        acted = True

    return acted


# ============================================================
# 카메라 초기화
# ============================================================

def init_camera():
    try:
        from picamera2 import Picamera2
        print("[INFO] Initializing camera...")
        picam2 = Picamera2()
        config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)})
        picam2.configure(config)
        picam2.start()
        time.sleep(2)
        print("[✓] Camera ready")

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
        return None


# ============================================================
# 메인 루프 (단일 CRUISE 상태)
# ============================================================

def lane_follow_loop():
    print("=" * 70)
    print(" Line Tracer + Object Trigger (Simplified)")
    print("=" * 70)
    print("[INFO] Press Ctrl+C to stop\n")

    camera = init_camera()
    if not camera:
        return

    # HSV 범위 정밀화 (Saturation/Value 최소값 상향으로 노이즈 감소)
    lower_cyan = np.array([80, 50, 50])
    upper_cyan = np.array([100, 255, 255])

    start_time = time.time()
    frame_count = 0

    # ROI 크기 확대 (라인 인식 범위 증가)
    BOX_WIDTH, BOX_HEIGHT = 240, 160

    # 동적 균형 임계값 (속도 기반)
    BASE_BALANCE_THRESHOLD = 0.35
    HIGH_SPEED_BALANCE_THRESHOLD = 0.25

    # 픽셀 임계값 조정 (ROI 증가에 맞춰 조정)
    PIXEL_THRESHOLD = 1000  # 240x160x2 = 76,800 픽셀의 약 1.3%

    # 라인 손실 임계값 (속도 기반 동적 조정)
    BASE_LINE_LOST_THRESHOLD = 2.0
    HIGH_SPEED_LINE_LOST_THRESHOLD = 1.0

    line_lost_time = None

    try:
        while True:
            ret, frame = camera.read()
            if not ret:
                print("[ERROR] Failed to read frame")
                break

            frame = cv2.flip(frame, -1)
            height, width = frame.shape[:2]
            frame_count += 1
            if frame_count % 3 == 0:
                with shared_state.lock:
                    shared_state.latest_frame = frame.copy()

            # 좌우 ROI 영역 추출
            left_box = frame[height-BOX_HEIGHT:height, 0:BOX_WIDTH]
            right_box = frame[height-BOX_HEIGHT:height, width-BOX_WIDTH:width]
            hsv_left = cv2.cvtColor(left_box, cv2.COLOR_BGR2HSV)
            hsv_right = cv2.cvtColor(right_box, cv2.COLOR_BGR2HSV)
            mask_left = cv2.inRange(hsv_left, lower_cyan, upper_cyan)
            mask_right = cv2.inRange(hsv_right, lower_cyan, upper_cyan)

            kernel = np.ones((3, 3), np.uint8)
            mask_left = cv2.erode(mask_left, kernel, iterations=2)
            mask_left = cv2.dilate(mask_left, kernel, iterations=3)
            mask_right = cv2.erode(mask_right, kernel, iterations=2)
            mask_right = cv2.dilate(mask_right, kernel, iterations=3)

            left_pixels = cv2.countNonZero(mask_left)
            right_pixels = cv2.countNonZero(mask_right)
            total_pixels = left_pixels + right_pixels

            if total_pixels > 0:
                left_ratio = left_pixels / total_pixels
                right_ratio = right_pixels / total_pixels
            else:
                left_ratio = right_ratio = 0.0

            diff = abs(left_ratio - right_ratio)

            # 동적 임계값 계산 (속도 기반)
            is_high_speed = SPEED_FORWARD > 0.6
            current_balance_threshold = HIGH_SPEED_BALANCE_THRESHOLD if is_high_speed else BASE_BALANCE_THRESHOLD
            current_line_lost_threshold = HIGH_SPEED_LINE_LOST_THRESHOLD if is_high_speed else BASE_LINE_LOST_THRESHOLD

            # 차선 인식 성공 시
            if total_pixels >= PIXEL_THRESHOLD:
                if diff < current_balance_threshold:
                    motor_forward()
                elif left_pixels > right_pixels:
                    # 편차에 비례한 회전 강도 계산
                    turn_intensity = min(1.0, diff / 0.5)  # 최대 편차 50%로 정규화
                    motor_right(turn_intensity)
                else:
                    turn_intensity = min(1.0, diff / 0.5)
                    motor_left(turn_intensity)
                line_lost_time = None

                # 객체 트리거 처리
                handle_runtime_triggers()

            else:
                # 라인 손실 → 수동 모드 진입
                if line_lost_time is None:
                    line_lost_time = time.time()
                lost_duration = time.time() - line_lost_time

                if lost_duration >= current_line_lost_threshold:
                    motor_stop()
                    print("라인 이탈 - 수동/표지판 모드 전환")

                    waiting = True
                    while waiting:
                        if try_branch_by_trigger():
                            print("표지판 수행 → 자동 복귀")
                            line_lost_time = None
                            waiting = False
                            break

                        user_input = get_user_input()
                        if user_input == 'a':
                            print("→ 좌회전(수동)"); motor_forward(); time.sleep(0.5); motor_left(1.0)
                        elif user_input == 'd':
                            print("→ 우회전(수동)"); motor_forward(); time.sleep(0.5); motor_right(1.0)
                        elif user_input == 'w':
                            print("→ 직진(수동)"); motor_forward()

                        ret2, temp = camera.read()
                        if not ret2: break
                        temp = cv2.flip(temp, -1)
                        th, tw = temp.shape[:2]
                        t_left = temp[th-BOX_HEIGHT:th, 0:BOX_WIDTH]
                        t_right = temp[th-BOX_HEIGHT:th, tw-BOX_WIDTH:tw]
                        t_mask_left = cv2.inRange(cv2.cvtColor(t_left, cv2.COLOR_BGR2HSV), lower_cyan, upper_cyan)
                        t_mask_right = cv2.inRange(cv2.cvtColor(t_right, cv2.COLOR_BGR2HSV), lower_cyan, upper_cyan)
                        t_total = cv2.countNonZero(t_mask_left) + cv2.countNonZero(t_mask_right)
                        if t_total >= PIXEL_THRESHOLD:
                            print("✓ 라인 복귀 → 자동 모드 전환")
                            waiting = False
                        time.sleep(0.05)

            time.sleep(0.03)

    except KeyboardInterrupt:
        print("\n[INFO] Lane tracer stopped by user.")

    finally:
        motor_stop()
        camera.release()
        print("[✓] Lane tracer cleanup complete")
