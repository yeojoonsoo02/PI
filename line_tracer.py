"""
Line Tracer - 좌우 균형 청록색 라인 추적
화면을 좌우로 나눠서 청록색(Cyan) 픽셀 양을 비교하여 중앙 유지
"""
import cv2
import numpy as np
import time
from gpiozero import DigitalOutputDevice, PWMOutputDevice

# ============================================================
# 모터 설정
# ============================================================
PWMA = PWMOutputDevice(18)
AIN1 = DigitalOutputDevice(22)
AIN2 = DigitalOutputDevice(27)

PWMB = PWMOutputDevice(23)
BIN1 = DigitalOutputDevice(25)
BIN2 = DigitalOutputDevice(24)

# 속도 설정
SPEED_FORWARD = 0.40
SPEED_TURN = 0.35

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

def motor_left():
    """좌회전 (왼쪽 정지, 오른쪽 전진)"""
    AIN1.value = 1
    AIN2.value = 0
    PWMA.value = 0.0
    BIN1.value = 0
    BIN2.value = 1
    PWMB.value = SPEED_TURN

def motor_right():
    """우회전 (왼쪽 전진, 오른쪽 정지)"""
    AIN1.value = 0
    AIN2.value = 1
    PWMA.value = SPEED_TURN
    BIN1.value = 1
    BIN2.value = 0
    PWMB.value = 0.0

def motor_stop():
    """정지"""
    AIN1.value = 0
    AIN2.value = 1
    PWMA.value = 0.0
    BIN1.value = 1
    BIN2.value = 0
    PWMB.value = 0.0

# ============================================================
# 카메라 초기화
# ============================================================
def init_camera():
    """카메라 초기화"""
    try:
        from picamera2 import Picamera2
        print("[INFO] Initializing camera...")

        picam2 = Picamera2()
        config = picam2.create_preview_configuration(
            main={"format": "RGB888", "size": (320, 240)}
        )
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
# 메인 루프
# ============================================================
def main():
    """메인 루프"""
    print("=" * 70)
    print(" Line Tracer - 좌우 균형 청록색 라인 추적")
    print("=" * 70)
    print()
    print("원리: 화면 좌/우 가장자리 영역(각 30%)의 청록색 픽셀 수를 비교")
    print("     중앙 초록색 영역은 무시하고 양쪽 얇은 라인만 추적")
    print("     좌우 균형을 맞추면서 전진")
    print()
    print("[INFO] Press Ctrl+C to stop")
    print()

    camera = init_camera()
    if not camera:
        return

    # HSV 범위 - 청록색(Cyan) 라인용
    # 테스트 결과 최적값: 매우 넓은 범위 (평균 13,635 pixels)
    lower_cyan = np.array([65, 20, 20])
    upper_cyan = np.array([115, 255, 255])

    start_time = time.time()
    frame_count = 0
    action_stats = {"FORWARD": 0, "LEFT": 0, "RIGHT": 0, "STOP": 0}

    # 좌우 픽셀 차이 허용 범위
    BALANCE_THRESHOLD = 0.25  # 25% 차이까지 허용 (양쪽 가장자리 라인용)

    try:
        while True:
            ret, frame = camera.read()
            if not ret:
                print("[ERROR] Failed to read frame")
                break

            frame_count += 1

            # 이미지 뒤집기
            frame = cv2.flip(frame, -1)

            # ROI: 화면 하단 60% (바닥만 보기)
            height, width = frame.shape[:2]
            roi_start = int(height * 0.4)
            roi = frame[roi_start:, :]
            roi_height, roi_width = roi.shape[:2]

            # BGR → HSV 변환
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

            # 청록색 마스크 생성
            mask = cv2.inRange(hsv, lower_cyan, upper_cyan)

            # 노이즈 제거
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.erode(mask, kernel, iterations=2)
            mask = cv2.dilate(mask, kernel, iterations=3)

            # 화면을 좌/우 가장자리 영역으로 나누기
            # 중앙 부분은 제외하고 좌우 끝부분만 사용
            edge_width = int(roi_width * 0.3)  # 좌우 각각 30%씩만 사용

            left_mask = mask[:, :edge_width]                    # 왼쪽 30%
            right_mask = mask[:, -edge_width:]                  # 오른쪽 30%
            # 중앙 40%는 무시 (초록색 영역 제외)

            # 각 영역의 청록색 픽셀 수 계산
            left_pixels = cv2.countNonZero(left_mask)
            right_pixels = cv2.countNonZero(right_mask)
            total_pixels = left_pixels + right_pixels

            # 좌우 비율 계산
            if total_pixels > 0:
                left_ratio = left_pixels / total_pixels
                right_ratio = right_pixels / total_pixels
            else:
                left_ratio = 0.0
                right_ratio = 0.0

            # 좌우 차이
            diff = abs(left_ratio - right_ratio)

            # 조향 결정
            action = "STOP"

            if total_pixels < 200:
                # 청록색이 거의 없음 → 정지 (양쪽 라인이므로 최소 200)
                motor_stop()
                action = "STOP"

            elif diff < BALANCE_THRESHOLD:
                # 좌우 균형 잡힘 → 전진
                motor_forward()
                action = "FORWARD"

            elif left_pixels > right_pixels:
                # 왼쪽에 청록색이 많음 → 우회전 (라인에서 멀어지도록)
                motor_right()
                action = "RIGHT"

            else:
                # 오른쪽에 청록색이 많음 → 좌회전 (라인에서 멀어지도록)
                motor_left()
                action = "LEFT"

            action_stats[action] += 1

            # 로그 출력 (모든 프레임마다)
            runtime = int(time.time() - start_time)

            # 상태 아이콘
            if action == "FORWARD":
                icon = "↑"
            elif action == "LEFT":
                icon = "←"
            elif action == "RIGHT":
                icon = "→"
            else:
                icon = "■"

            # 균형 상태 표시
            balance_bar = create_balance_bar(left_ratio, right_ratio)

            # 로그 출력 (가장자리 영역 크기도 표시)
            print(f"[{runtime:3d}s] F:{frame_count:5d} | "
                  f"Edge:{edge_width}x{roi_height} | "
                  f"L:{left_pixels:4d} R:{right_pixels:4d} Tot:{total_pixels:4d} | "
                  f"{balance_bar} | "
                  f"D:{diff:.2f} | {icon} {action:7s}")

            time.sleep(0.03)

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
        for action in ["FORWARD", "LEFT", "RIGHT", "STOP"]:
            count = action_stats[action]
            percentage = (count / max(frame_count, 1)) * 100
            bar = "█" * int(percentage / 2)
            print(f"  {action:8s} : {count:5d} ({percentage:5.1f}%) {bar}")
        print()

        # 성능 분석
        forward_ratio = action_stats["FORWARD"] / max(frame_count, 1)
        stop_ratio = action_stats["STOP"] / max(frame_count, 1)

        if stop_ratio > 0.7:
            print("✗ 청록색 감지 실패 (대부분 정지)")
            print("  → HSV 범위 조정 필요")
        elif forward_ratio > 0.5:
            print("✓ 좋은 성능 (직진 비율 높음)")
        elif forward_ratio > 0.3:
            print("⚠ 보통 성능 (회전이 많음)")
        else:
            print("⚠ 불안정한 주행 (회전 과다)")

        print("=" * 70)

        motor_stop()
        PWMA.value = 0.0
        PWMB.value = 0.0
        camera.release()
        print("[✓] Cleanup complete")

def create_balance_bar(left_ratio, right_ratio):
    """좌우 균형 시각화 바 생성"""
    bar_length = 20

    if left_ratio == 0 and right_ratio == 0:
        return "[" + " " * bar_length + "]"

    left_bars = int(left_ratio * bar_length)
    right_bars = int(right_ratio * bar_length)

    # 좌우 균형 표시
    bar = "L[" + "█" * left_bars + " " * (bar_length - left_bars) + "|" + \
          "█" * right_bars + " " * (bar_length - right_bars) + "]R"

    return bar

if __name__ == '__main__':
    main()
