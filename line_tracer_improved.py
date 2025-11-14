"""
Line Tracer (Improved Version) - 개선된 라인 트레이싱
잘 작동하는 코드 베이스 + 성능 개선
"""
import cv2
import numpy as np
import time
import sys
import select
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
SPEED_FORWARD = 0.75  # 직진 속도 (빠름)
SPEED_TURN = 0.55     # 회전 속도 (코너링 안정성)
SPEED_SPIN = 0.70     # 제자리 회전 속도 (빠름)

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
    PWMA.value = SPEED_TURN * left_ratio  # 왼쪽 속도 조절
    BIN1.value = 0
    BIN2.value = 1
    PWMB.value = SPEED_TURN * right_ratio  # 오른쪽 속도 조절

def motor_right(intensity=1.0):
    """우회전 - intensity로 회전 강도 조절 (0.0~1.0)"""
    left_ratio = 1.0 * intensity
    right_ratio = 0.25 * intensity
    AIN1.value = 0
    AIN2.value = 1
    PWMA.value = SPEED_TURN * left_ratio  # 왼쪽 속도 조절
    BIN1.value = 0
    BIN2.value = 1
    PWMB.value = SPEED_TURN * right_ratio  # 오른쪽 속도 조절

def motor_spin_right():
    """제자리 우회전 (왼쪽 후진, 오른쪽 전진) - 라인 찾기용"""
    AIN1.value = 1  # 왼쪽 후진
    AIN2.value = 0
    PWMA.value = SPEED_SPIN
    BIN1.value = 0  # 오른쪽 전진
    BIN2.value = 1
    PWMB.value = SPEED_SPIN

def motor_spin_left():
    """제자리 좌회전 (왼쪽 전진, 오른쪽 후진) - 라인 찾기용"""
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
# 카메라 초기화
# ============================================================
def init_camera():
    """카메라 초기화 - 해상도 증가 버전"""
    try:
        from picamera2 import Picamera2
        print("[INFO] Initializing camera...")

        picam2 = Picamera2()
        # 해상도 증가: 320x240 -> 640x480 (필요시 480x360으로 조정 가능)
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
        print("[INFO] Falling back to 480x360...")
        try:
            # 대체 해상도로 재시도
            picam2 = Picamera2()
            config = picam2.create_preview_configuration(
                main={"format": "RGB888", "size": (480, 360)}
            )
            picam2.configure(config)
            picam2.start()
            time.sleep(2)
            print("[✓] Camera ready (480x360)")

            class CameraWrapper:
                def read(self):
                    frame = picam2.capture_array()
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    return True, frame
                def release(self):
                    picam2.stop()
            return CameraWrapper()
        except:
            return None

# ============================================================
# 메인 루프
# ============================================================
def main():
    """메인 루프 - 개선된 버전"""
    print("=" * 70)
    print(" Line Tracer (Improved) - 개선된 라인 트레이서")
    print("=" * 70)
    print()
    print("개선 사항:")
    print("  • 해상도 증가 (640x480)")
    print("  • 교차로 감지 기능")
    print("  • 전방 중앙 박스로 수평선 감지")
    print("  • 비례 제어 시스템")
    print("  • 동적 임계값")
    print()
    print("교차로 감지:")
    print("  → 전방 수평선 + 좌우 라인 없음 = 정지")
    print("  [a] - 수동 좌회전")
    print("  [d] - 수동 우회전")
    print("  [w] - 수동 직진")
    print("  [s] - 정지")
    print()
    print("[INFO] Press Ctrl+C to stop")
    print()

    camera = init_camera()
    if not camera:
        return

    # HSV 범위 - 청록색(Cyan) 라인용
    # 개선된 정밀 범위
    lower_cyan = np.array([80, 50, 50])   # 더 정밀한 범위
    upper_cyan = np.array([100, 255, 255])

    start_time = time.time()
    frame_count = 0
    action_stats = {"FORWARD": 0, "LEFT": 0, "RIGHT": 0, "STOP": 0, "INTERSECTION": 0}

    # 동적 균형 임계값 (속도 기반)
    BASE_BALANCE_THRESHOLD = 0.35  # 기본 균형 임계값
    HIGH_SPEED_BALANCE_THRESHOLD = 0.25  # 고속 시 균형 임계값

    # 박스 크기 설정 (해상도에 맞춰 증가)
    BOX_WIDTH_RATIO = 0.25   # 화면 너비의 25%
    BOX_HEIGHT_RATIO = 0.25  # 화면 높이의 25%

    # 픽셀 임계값 (ROI 크기에 비례)
    MIN_PIXEL_RATIO = 0.02  # ROI의 2%

    # 한쪽 라인 없을 때 직진 타이머
    one_side_missing_time = None
    one_side_missing_direction = None
    STRAIGHT_DURATION = 0.5  # 한쪽 없을 때 직진 시간

    # 라인 탐색 방향 (마지막으로 본 방향)
    last_seen_side = None  # 'LEFT' or 'RIGHT'

    # 교차로 모드 관련 변수
    intersection_mode = False  # 교차로에서 정지 중인지 여부
    intersection_exit_time = None  # 교차로 탈출 시간
    INTERSECTION_EXIT_DURATION = 2.0  # 교차로 탈출 후 감지 무시 시간

    print("\n[INFO] 교차로 감지 시:")
    print("  → 자동 정지 후 선택 대기")
    print("  [a] 좌회전 | [d] 우회전 | [w] 직진")
    print()

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

            # 동적 박스 크기 계산
            BOX_WIDTH = int(width * BOX_WIDTH_RATIO)
            BOX_HEIGHT = int(height * BOX_HEIGHT_RATIO)

            # 동적 픽셀 임계값
            PIXEL_THRESHOLD = int(BOX_WIDTH * BOX_HEIGHT * 2 * MIN_PIXEL_RATIO)

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

            # 전방 중앙 박스 (교차로 감지용) - 화면 중앙 상단
            center_box_width = int(width * 0.6)  # 화면 너비의 60%
            center_box_height = int(height * 0.15)  # 화면 높이의 15%
            center_box_x1 = (width - center_box_width) // 2
            center_box_y1 = int(height * 0.3)  # 화면 상단 30% 위치
            center_box_x2 = center_box_x1 + center_box_width
            center_box_y2 = center_box_y1 + center_box_height
            center_box = frame[center_box_y1:center_box_y2, center_box_x1:center_box_x2]

            # 좌측 박스: BGR → HSV → 청록색 마스크
            hsv_left = cv2.cvtColor(left_box, cv2.COLOR_BGR2HSV)
            mask_left = cv2.inRange(hsv_left, lower_cyan, upper_cyan)

            # 노이즈 제거
            kernel = np.ones((3, 3), np.uint8)
            mask_left = cv2.erode(mask_left, kernel, iterations=2)
            mask_left = cv2.dilate(mask_left, kernel, iterations=3)

            # 우측 박스: BGR → HSV → 청록색 마스크
            hsv_right = cv2.cvtColor(right_box, cv2.COLOR_BGR2HSV)
            mask_right = cv2.inRange(hsv_right, lower_cyan, upper_cyan)

            # 노이즈 제거
            mask_right = cv2.erode(mask_right, kernel, iterations=2)
            mask_right = cv2.dilate(mask_right, kernel, iterations=3)

            # 전방 중앙 박스: BGR → HSV → 청록색 마스크 (교차로 감지)
            hsv_center = cv2.cvtColor(center_box, cv2.COLOR_BGR2HSV)
            mask_center = cv2.inRange(hsv_center, lower_cyan, upper_cyan)

            # 노이즈 제거
            mask_center = cv2.erode(mask_center, kernel, iterations=2)
            mask_center = cv2.dilate(mask_center, kernel, iterations=3)

            # 각 박스의 청록색 픽셀 수 계산
            left_pixels = cv2.countNonZero(mask_left)
            right_pixels = cv2.countNonZero(mask_right)
            center_pixels = cv2.countNonZero(mask_center)
            total_pixels = left_pixels + right_pixels

            # 교차로 감지 임계값 (전방 박스의 30% 이상이 청록색이면 교차로)
            CENTER_THRESHOLD = int(center_box_width * center_box_height * 0.3)

            # 좌우 비율 계산
            if total_pixels > 0:
                left_ratio = left_pixels / total_pixels
                right_ratio = right_pixels / total_pixels
            else:
                left_ratio = 0.0
                right_ratio = 0.0

            # 좌우 차이
            diff = abs(left_ratio - right_ratio)

            # 동적 임계값 계산 (속도 기반)
            is_high_speed = SPEED_FORWARD > 0.6
            current_balance_threshold = HIGH_SPEED_BALANCE_THRESHOLD if is_high_speed else BASE_BALANCE_THRESHOLD

            # 조향 결정
            action = "STOP"

            # 교차로 모드에서 키보드 입력 처리
            if intersection_mode:
                user_input = get_user_input()
                if user_input:
                    print(f"\n[교차로] 선택: {user_input}")

                    if user_input == 'w':
                        motor_forward()
                        action = "FORWARD"
                        print("  → 직진 선택")
                        intersection_mode = False
                        intersection_exit_time = time.time()
                    elif user_input == 'a':
                        motor_left(1.0)
                        action = "LEFT"
                        print("  → 좌회전 선택")
                        intersection_mode = False
                        intersection_exit_time = time.time()
                    elif user_input == 'd':
                        motor_right(1.0)
                        action = "RIGHT"
                        print("  → 우회전 선택")
                        intersection_mode = False
                        intersection_exit_time = time.time()
                    elif user_input == 's':
                        motor_stop()
                        action = "STOP"
                        print("  → 정지 유지")
                else:
                    # 키보드 입력 대기 중
                    motor_stop()
                    action = "INTERSECTION"
                continue

            # 교차로 탈출 중이면 일정 시간 교차로 감지 무시
            if intersection_exit_time:
                elapsed = time.time() - intersection_exit_time
                if elapsed < INTERSECTION_EXIT_DURATION:
                    # 교차로 탈출 중 - 이전 동작 유지하고 교차로 감지 무시
                    pass  # 이전 action 유지
                else:
                    # 탈출 완료
                    intersection_exit_time = None

            # 교차로 감지 (전방에 수평선이 있고 좌우 픽셀이 적을 때)
            elif not intersection_exit_time and center_pixels > CENTER_THRESHOLD and total_pixels < PIXEL_THRESHOLD * 2:
                if not intersection_mode:
                    motor_stop()
                    action = "INTERSECTION"
                    intersection_mode = True
                    print(f"\n🛑 교차로 감지! 전방:{center_pixels} 좌우:{total_pixels}")
                    print("  [a] 좌회전 | [d] 우회전 | [w] 직진 | [s] 정지")
                    print("  선택 대기 중...")

            # 라인이 거의 안 보일 때 (교차로가 아닌 경우)
            elif total_pixels < PIXEL_THRESHOLD:
                motor_stop()
                action = "STOP"

            # 라인이 충분히 보일 때 조향 제어
            elif total_pixels >= PIXEL_THRESHOLD:

                if diff < current_balance_threshold:
                    # 좌우 균형 잡힘 → 전진
                    motor_forward()
                    action = "FORWARD"
                    one_side_missing_time = None
                    one_side_missing_direction = None

                elif left_pixels > right_pixels:
                    # 왼쪽에 청록색이 많음 → 우회전 필요
                    last_seen_side = 'LEFT'  # 라인이 왼쪽에 있음

                    # 편차에 비례한 회전 강도 계산
                    turn_intensity = min(1.0, diff / 0.5)  # 최대 편차 50%로 정규화

                    if right_pixels < 50:
                        # 오른쪽 라인이 거의 없음
                        if one_side_missing_time is None or one_side_missing_direction != 'RIGHT':
                            one_side_missing_time = time.time()
                            one_side_missing_direction = 'RIGHT'

                        elapsed = time.time() - one_side_missing_time
                        if elapsed < STRAIGHT_DURATION:
                            # 직진 유지
                            motor_forward()
                            action = "FORWARD"
                        else:
                            # 강한 우회전
                            motor_right(min(1.0, turn_intensity * 1.5))
                            action = "RIGHT"
                    else:
                        # 일반 우회전 (비례 제어)
                        motor_right(turn_intensity)
                        action = "RIGHT"
                        one_side_missing_time = None
                        one_side_missing_direction = None

                else:
                    # 오른쪽에 청록색이 많음 → 좌회전 필요
                    last_seen_side = 'RIGHT'  # 라인이 오른쪽에 있음

                    # 편차에 비례한 회전 강도 계산
                    turn_intensity = min(1.0, diff / 0.5)

                    if left_pixels < 50:
                        # 왼쪽 라인이 거의 없음
                        if one_side_missing_time is None or one_side_missing_direction != 'LEFT':
                            one_side_missing_time = time.time()
                            one_side_missing_direction = 'LEFT'

                        elapsed = time.time() - one_side_missing_time
                        if elapsed < STRAIGHT_DURATION:
                            # 직진 유지
                            motor_forward()
                            action = "FORWARD"
                        else:
                            # 강한 좌회전
                            motor_left(min(1.0, turn_intensity * 1.5))
                            action = "LEFT"
                    else:
                        # 일반 좌회전 (비례 제어)
                        motor_left(turn_intensity)
                        action = "LEFT"
                        one_side_missing_time = None
                        one_side_missing_direction = None

            # 통계 업데이트
            action_stats[action] += 1

            # 로그 출력 (10프레임마다)
            if frame_count % 10 == 0:
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

            time.sleep(0.02)  # 더 빠른 반응을 위해 0.03 → 0.02

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
        print(f"  균형 임계값: {current_balance_threshold:.2f}")
        print("=" * 70)

        # 모터 완전 정지
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