"""
Line Tracer (Corner Detection) - 좌하/우하 코너 박스 청록색 라인 추적
화면 하단 좌측/우측 코너에 작은 박스를 만들어서 청록색 픽셀 비교
"""
import cv2
import numpy as np
import time
import random
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

def motor_stop():
    """정지"""
    # 두 모터 모두 완전 정지 (방향 일치)
    AIN1.value = 0
    AIN2.value = 0  # 왼쪽 모터 완전 정지
    PWMA.value = 0.0
    BIN1.value = 0
    BIN2.value = 0  # 오른쪽 모터 완전 정지
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
    """카메라 초기화"""
    try:
        from picamera2 import Picamera2
        print("[INFO] Initializing camera...")

        picam2 = Picamera2()
        # 해상도 증가 (320x240 → 640x480)
        config = picam2.create_preview_configuration(
            main={"format": "RGB888", "size": (640, 480)}
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
# 색상 자동 캘리브레이션
# ============================================================
def calibrate_color(camera, box_width=80, box_height=60, sample_frames=30):
    """
    좌우 박스에서 실제 라인 색상을 샘플링하여 HSV 범위 자동 설정
    """
    print("\n" + "=" * 70)
    print(" 🎨 색상 자동 캘리브레이션 시작")
    print("=" * 70)
    print("라인을 좌우 박스에 위치시켜 주세요...")
    print(f"샘플링: {sample_frames}프레임")
    print()

    h_values = []  # Hue 값들
    s_values = []  # Saturation 값들
    v_values = []  # Value 값들

    for i in range(sample_frames):
        ret, frame = camera.read()
        if not ret:
            continue

        # 이미지 뒤집기
        frame = cv2.flip(frame, -1)
        height, width = frame.shape[:2]

        # 좌하단 박스
        left_box = frame[height-box_height:height, 0:box_width]
        # 우하단 박스
        right_box = frame[height-box_height:height, width-box_width:width]

        # 좌우 박스 합치기
        for box in [left_box, right_box]:
            hsv = cv2.cvtColor(box, cv2.COLOR_BGR2HSV)

            # 청록색 범위의 픽셀만 샘플링 (H=80~110, S>50, V>50)
            # 배경(낮은 채도)이나 다른 색상 제외
            mask_cyan = (hsv[:, :, 0] >= 80) & (hsv[:, :, 0] <= 110) & \
                        (hsv[:, :, 1] > 50) & \
                        (hsv[:, :, 2] > 50)

            if np.sum(mask_cyan) > 50:  # 충분한 픽셀이 있을 때만
                h_values.extend(hsv[mask_cyan, 0].flatten().tolist())
                s_values.extend(hsv[mask_cyan, 1].flatten().tolist())
                v_values.extend(hsv[mask_cyan, 2].flatten().tolist())

        # 진행 상황 표시
        if (i + 1) % 10 == 0:
            print(f"  샘플링 중... {i+1}/{sample_frames} ({len(h_values)} pixels)")

        time.sleep(0.05)

    if len(h_values) < 500:
        print("\n⚠️  샘플 부족! 기본값 사용")
        print(f"   (청록색 픽셀이 {len(h_values)}개만 감지됨)")
        # 개선된 기본값 (더 정밀한 청록색 범위)
        return np.array([80, 50, 50]), np.array([100, 255, 255])

    # 통계 계산 (중앙값 사용 - 노이즈에 강함)
    h_median = np.median(h_values)
    s_median = np.median(s_values)
    v_median = np.median(v_values)

    # 감지된 색상이 청록색 범위인지 검증
    if not (80 <= h_median <= 110) or s_median < 30:
        print("\n⚠️  감지된 색상이 청록색이 아닙니다! 기본값 사용")
        print(f"   (H={h_median:.1f}, S={s_median:.1f} - 청록색 범위: H=80~110, S>30)")
        # 개선된 기본값 (더 정밀한 청록색 범위)
        return np.array([80, 50, 50]), np.array([100, 255, 255])

    # HSV 범위 설정 (넉넉하게)
    h_range = 20  # Hue ±20
    s_range = 80  # Saturation -80 ~ +100
    v_range = 100  # Value -100 ~ +150

    lower_h = max(0, int(h_median - h_range))
    upper_h = min(179, int(h_median + h_range))

    lower_s = max(0, int(s_median - s_range))
    upper_s = min(255, int(s_median + 100))  # 위쪽은 더 넉넉하게

    lower_v = max(0, int(v_median - v_range))
    upper_v = min(255, int(v_median + 150))  # 위쪽은 더 넉넉하게

    lower_bound = np.array([lower_h, lower_s, lower_v])
    upper_bound = np.array([upper_h, upper_s, upper_v])

    print()
    print("=" * 70)
    print(" ✓ 캘리브레이션 완료")
    print("=" * 70)
    print(f"샘플 픽셀 수: {len(h_values)}")
    print()
    print("검출된 색상 (중앙값):")
    print(f"  H (색상)  : {h_median:.1f}")
    print(f"  S (채도)  : {s_median:.1f}")
    print(f"  V (명도)  : {v_median:.1f}")
    print()
    print("설정된 HSV 범위:")
    print(f"  Lower: H={lower_h:3d}, S={lower_s:3d}, V={lower_v:3d}")
    print(f"  Upper: H={upper_h:3d}, S={upper_s:3d}, V={upper_v:3d}")
    print("=" * 70)
    print()

    time.sleep(1)

    return lower_bound, upper_bound

# ============================================================
# 메인 루프
# ============================================================
def main():
    """메인 루프"""
    print("=" * 70)
    print(" Line Tracer (Corner Detection) - 좌하/우하 박스 추적")
    print("=" * 70)
    print()
    print("원리: 화면 하단 좌측/우측 코너에 작은 박스 ROI 생성")
    print("     각 박스의 청록색 픽셀 수를 비교하여 균형 유지")
    print("     좌우 균형을 맞추면서 전진")
    print()
    print("라인 이탈 시 수동 제어:")
    print("  [a] - 좌회전")
    print("  [d] - 우회전")
    print("  [w] - 직진")
    print()
    print("[INFO] Press Ctrl+C to stop")
    print()

    camera = init_camera()
    if not camera:
        return

    # 박스 크기 설정 (해상도 증가에 맞춰 확대)
    BOX_WIDTH = 160   # 박스 너비 (640x480 기준 25%)
    BOX_HEIGHT = 120  # 박스 높이 (640x480 기준 25%)

    # 🎨 색상 자동 캘리브레이션
    lower_cyan, upper_cyan = calibrate_color(camera, BOX_WIDTH, BOX_HEIGHT, sample_frames=30)

    start_time = time.time()
    frame_count = 0
    action_stats = {"FORWARD": 0, "LEFT": 0, "RIGHT": 0, "STOP": 0, "MANUAL": 0}

    # 동적 균형 임계값 (속도 기반)
    BASE_BALANCE_THRESHOLD = 0.35  # 기본 균형 임계값
    HIGH_SPEED_BALANCE_THRESHOLD = 0.25  # 고속 시 균형 임계값

    # 픽셀 임계값 (ROI 크기에 비례)
    MIN_PIXEL_RATIO = 0.02  # ROI의 2%
    PIXEL_THRESHOLD = int(BOX_WIDTH * BOX_HEIGHT * 2 * MIN_PIXEL_RATIO)  # ~768 픽셀

    # 라인 탐색용 변수
    last_seen_side = None  # 마지막으로 라인이 보인 쪽 ('LEFT' or 'RIGHT')
    line_lost_time = None  # 라인을 잃은 시각
    BASE_LINE_LOST_THRESHOLD = 2.0  # 기본 라인 이탈 판정 시간 (초)
    HIGH_SPEED_LINE_LOST_THRESHOLD = 1.0  # 고속 시 라인 이탈 판정 시간

    # 한쪽 라인 없을 때 직진 타이머
    one_side_missing_time = None  # 한쪽 라인이 없어진 시각
    one_side_missing_direction = None  # 없어진 방향 ('LEFT' or 'RIGHT')
    STRAIGHT_DURATION = 0.5  # 한쪽 없을 때 직진 시간 (초)

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

            # 좌하단 박스 (왼쪽 아래 코너)
            # x: 왼쪽 끝에서 시작
            # y: 아래에서 BOX_HEIGHT만큼
            left_box_x1 = 0
            left_box_y1 = height - BOX_HEIGHT
            left_box_x2 = BOX_WIDTH
            left_box_y2 = height

            left_box = frame[left_box_y1:left_box_y2, left_box_x1:left_box_x2]

            # 우하단 박스 (오른쪽 아래 코너)
            # x: 오른쪽 끝에서 BOX_WIDTH만큼
            # y: 아래에서 BOX_HEIGHT만큼
            right_box_x1 = width - BOX_WIDTH
            right_box_y1 = height - BOX_HEIGHT
            right_box_x2 = width
            right_box_y2 = height

            right_box = frame[right_box_y1:right_box_y2, right_box_x1:right_box_x2]

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

            # 각 박스의 청록색 픽셀 수 계산
            left_pixels = cv2.countNonZero(mask_left)
            right_pixels = cv2.countNonZero(mask_right)
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

            # 동적 임계값 계산 (속도 기반)
            is_high_speed = SPEED_FORWARD > 0.6
            current_balance_threshold = HIGH_SPEED_BALANCE_THRESHOLD if is_high_speed else BASE_BALANCE_THRESHOLD
            current_line_lost_threshold = HIGH_SPEED_LINE_LOST_THRESHOLD if is_high_speed else BASE_LINE_LOST_THRESHOLD

            # 조향 결정
            action = "STOP"

            # 라인 이탈 시간 체크
            if total_pixels < PIXEL_THRESHOLD:
                # 라인 이탈 시작 시간 기록
                if line_lost_time is None:
                    line_lost_time = time.time()

                # 이탈 지속 시간 계산
                lost_duration = time.time() - line_lost_time

                # 동적 시간 이상 이탈 시 수동 제어 모드
                if lost_duration >= current_line_lost_threshold:
                    motor_stop()
                    action = "WAIT_INPUT"

                    print(f"\n{'='*70}")
                    print(f"⚠️  라인 {lost_duration:.1f}초 이탈! 수동 제어 모드")
                    print("  [a] 좌회전 | [d] 우회전 | [w] 직진")
                    print(f"{'='*70}\n")

                    # 사용자 입력 대기
                    waiting = True
                    manual_start_time = None

                    while waiting:
                        # 현재 프레임 읽기
                        ret, temp_frame = camera.read()
                        if ret:
                            temp_frame = cv2.flip(temp_frame, -1)
                            temp_height, temp_width = temp_frame.shape[:2]

                            # 좌우 박스 체크
                            temp_left_box = temp_frame[temp_height-BOX_HEIGHT:temp_height, 0:BOX_WIDTH]
                            temp_right_box = temp_frame[temp_height-BOX_HEIGHT:temp_height, temp_width-BOX_WIDTH:temp_width]

                            temp_hsv_left = cv2.cvtColor(temp_left_box, cv2.COLOR_BGR2HSV)
                            temp_mask_left = cv2.inRange(temp_hsv_left, lower_cyan, upper_cyan)
                            temp_left_pixels = cv2.countNonZero(temp_mask_left)

                            temp_hsv_right = cv2.cvtColor(temp_right_box, cv2.COLOR_BGR2HSV)
                            temp_mask_right = cv2.inRange(temp_hsv_right, lower_cyan, upper_cyan)
                            temp_right_pixels = cv2.countNonZero(temp_mask_right)

                            temp_total = temp_left_pixels + temp_right_pixels

                            # 수동 동작 중 시간 체크
                            if manual_start_time is not None:
                                elapsed = time.time() - manual_start_time

                                # 동작별 최대 시간 설정
                                if action == "MANUAL_FWD":
                                    max_duration = 2.0  # 직진 2초
                                    # 직진 중에만 라인 발견 시 복귀
                                    if temp_total >= PIXEL_THRESHOLD:
                                        motor_stop()
                                        print(f"✓ 라인 재발견! 자동 모드 복귀 (동작 {elapsed:.1f}초 후)")
                                        line_lost_time = None
                                        waiting = False
                                        break
                                else:  # MANUAL_LEFT or MANUAL_RIGHT
                                    max_duration = 4.0  # 회전 4초
                                    # 회전 중에는 라인 발견해도 무시하고 끝까지 회전

                                # 최대 시간 경과 시 자동 모드 복귀
                                if elapsed >= max_duration:
                                    print(f"⏱ {max_duration:.0f}초 경과, 자동 모드 복귀")
                                    line_lost_time = None  # 라인 이탈 타이머 초기화
                                    waiting = False  # 수동 모드 종료
                                    manual_start_time = None
                                    break

                        user_input = get_user_input()

                        if user_input == 'a' and manual_start_time is None:
                            print("→ 좌회전 실행")
                            print("   - 직진 0.5초 → 좌회전 4초")
                            motor_forward()
                            time.sleep(0.8)  # 0.5초 직진
                            motor_left(1.0)  # 수동 모드는 최대 강도
                            manual_start_time = time.time()
                            action = "MANUAL_LEFT"
                        elif user_input == 'd' and manual_start_time is None:
                            print("→ 우회전 실행")
                            print("   - 직진 0.5초 → 우회전 4초")
                            motor_forward()
                            time.sleep(0.8)  # 0.5초 직진
                            motor_right(1.0)  # 수동 모드는 최대 강도
                            manual_start_time = time.time()
                            action = "MANUAL_RIGHT"
                        elif user_input == 'w' and manual_start_time is None:
                            print("→ 직진 실행 (최대 2초)")
                            motor_forward()
                            manual_start_time = time.time()
                            action = "MANUAL_FWD"

                        time.sleep(0.05)  # CPU 부하 감소
                else:
                    # 2초 미만 이탈 시 정지
                    motor_stop()
                    action = "STOP"
            else:
                # 라인이 보이면 이탈 시간 초기화
                line_lost_time = None

            # 라인이 충분히 보일 때만 조향 제어
            if total_pixels >= PIXEL_THRESHOLD:
                if diff < current_balance_threshold:
                    # 좌우 균형 잡힘 → 전진
                    motor_forward()
                    action = "FORWARD"
                    # 양쪽에 라인이 보이면 타이머 초기화
                    last_seen_side = None
                    one_side_missing_time = None
                    one_side_missing_direction = None

                elif left_pixels > right_pixels:
                    # 왼쪽에 청록색이 많음 → 우회전 필요
                    if right_pixels < 50:
                        # 오른쪽이 거의 없음
                        if right_pixels == 0:
                            # 완전히 없음: 3프레임 직진 → 2프레임 회전 패턴 (3:2)
                            if frame_count % 5 < 3:
                                # 3프레임 연속 직진
                                motor_forward()
                                action = "FORWARD"
                            else:
                                # 2프레임 제자리 우회전 (왼쪽 전진, 오른쪽 후진)
                                AIN1.value = 0
                                AIN2.value = 1
                                PWMA.value = min(SPEED_TURN * 1.5, 1.0)  # 왼쪽 전진 150%
                                BIN1.value = 1  # 오른쪽 후진
                                BIN2.value = 0
                                PWMB.value = min(SPEED_TURN * 1.5, 1.0)  # 오른쪽 후진 150%
                                action = "RIGHT"
                        else:
                            # 부드러운 우회전 (조금씩 직진하며 회전)
                            AIN1.value = 0
                            AIN2.value = 1
                            PWMA.value = SPEED_TURN  # 왼쪽 100%
                            BIN1.value = 0
                            BIN2.value = 1
                            PWMB.value = SPEED_TURN * 0.4  # 오른쪽 40%
                            action = "RIGHT"
                    else:
                        # 오른쪽 라인 있음: 비례 우회전
                        # 편차에 비례한 회전 강도 계산
                        turn_intensity = min(1.0, diff / 0.5)  # 최대 편차 50%로 정규화
                        motor_right(turn_intensity)
                        action = "RIGHT"
                    # 왼쪽 라인이 마지막으로 보임
                    last_seen_side = 'LEFT'

                else:
                    # 오른쪽에 청록색이 많음 → 좌회전 필요
                    if left_pixels < 50:
                        # 왼쪽이 거의 없음
                        if left_pixels == 0:
                            # 완전히 없음: 3프레임 직진 → 2프레임 회전 패턴 (3:2)
                            if frame_count % 5 < 3:
                                # 3프레임 연속 직진
                                motor_forward()
                                action = "FORWARD"
                            else:
                                # 2프레임 제자리 좌회전 (왼쪽 후진, 오른쪽 전진)
                                AIN1.value = 1  # 왼쪽 후진
                                AIN2.value = 0
                                PWMA.value = min(SPEED_TURN * 1.5, 1.0)  # 왼쪽 후진 150%
                                BIN1.value = 0
                                BIN2.value = 1
                                PWMB.value = min(SPEED_TURN * 1.5, 1.0)  # 오른쪽 전진 150%
                                action = "LEFT"
                        else:
                            # 부드러운 좌회전 (조금씩 직진하며 회전)
                            AIN1.value = 0
                            AIN2.value = 1
                            PWMA.value = SPEED_TURN * 0.4  # 왼쪽 40%
                            BIN1.value = 0
                            BIN2.value = 1
                            PWMB.value = SPEED_TURN  # 오른쪽 100%
                            action = "LEFT"
                    else:
                        # 왼쪽 라인 있음: 비례 좌회전
                        # 편차에 비례한 회전 강도 계산
                        turn_intensity = min(1.0, diff / 0.5)  # 최대 편차 50%로 정규화
                        motor_left(turn_intensity)
                        action = "LEFT"
                    # 오른쪽 라인이 마지막으로 보임
                    last_seen_side = 'RIGHT'

            # 통계 업데이트 (MANUAL 계열은 모두 MANUAL로 집계)
            if action.startswith("MANUAL") or action == "WAIT_INPUT":
                action_stats["MANUAL"] += 1
            else:
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
            elif action == "MANUAL_LEFT":
                icon = "⇐"
            elif action == "MANUAL_RIGHT":
                icon = "⇒"
            elif action == "MANUAL_FWD":
                icon = "⇑"
            elif action == "WAIT_INPUT":
                icon = "⏸"
            else:
                icon = "■"

            # 균형 상태 표시
            balance_bar = create_balance_bar(left_ratio, right_ratio)

            # 로그 출력 (박스 크기와 위치 정보 포함)
            print(f"[{runtime:3d}s] F:{frame_count:5d} | "
                  f"Box:{BOX_WIDTH}x{BOX_HEIGHT} | "
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
        for action in ["FORWARD", "LEFT", "RIGHT", "MANUAL", "STOP"]:
            count = action_stats[action]
            percentage = (count / max(frame_count, 1)) * 100
            bar = "█" * int(percentage / 2)
            print(f"  {action:8s} : {count:5d} ({percentage:5.1f}%) {bar}")
        print()

        # 성능 분석
        forward_ratio = action_stats["FORWARD"] / max(frame_count, 1)
        manual_ratio = action_stats["MANUAL"] / max(frame_count, 1)
        stop_ratio = action_stats["STOP"] / max(frame_count, 1)

        if manual_ratio > 0.3:
            print("⚠ 라인 이탈 빈번 (수동 제어 비율 높음)")
            print("  → 속도 조정 또는 박스 위치 조정 필요")
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
        print("박스 위치:")
        print(f"  좌하단 박스: ({left_box_x1}, {left_box_y1}) ~ ({left_box_x2}, {left_box_y2})")
        print(f"  우하단 박스: ({right_box_x1}, {right_box_y1}) ~ ({right_box_x2}, {right_box_y2})")
        print()
        print("사용된 HSV 범위:")
        print(f"  Lower: H={lower_cyan[0]:3d}, S={lower_cyan[1]:3d}, V={lower_cyan[2]:3d}")
        print(f"  Upper: H={upper_cyan[0]:3d}, S={upper_cyan[1]:3d}, V={upper_cyan[2]:3d}")
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
