"""
Improved Dual ROI Line Tracer - 노란색 라인 전용
트랙을 벗어나지 않고 노란색 라인을 따라가는 개선된 로직
"""
import cv2
import numpy as np

USE_GPIO = False  # 실제 연결시 True
if USE_GPIO:
    import RPi.GPIO as GPIO
    IN1, IN2, IN3, IN4, ENA, ENB = 17, 18, 22, 23, 24, 25
    GPIO.setmode(GPIO.BCM)
    for p in (IN1, IN2, IN3, IN4, ENA, ENB):
        GPIO.setup(p, GPIO.OUT)
    pwmA = GPIO.PWM(ENA, 1000)
    pwmA.start(0)
    pwmB = GPIO.PWM(ENB, 1000)
    pwmB.start(0)


# 모터 제어 함수들
def motor_forward(speed=65):
    """전진"""
    if USE_GPIO:
        GPIO.output(IN1, True)
        GPIO.output(IN2, False)
        GPIO.output(IN3, True)
        GPIO.output(IN4, False)
        pwmA.ChangeDutyCycle(speed)
        pwmB.ChangeDutyCycle(speed)
    else:
        print(f"[MOTOR] FORWARD speed={speed}")


def motor_left(speed=50):
    """좌회전"""
    if USE_GPIO:
        GPIO.output(IN1, True)
        GPIO.output(IN2, False)
        GPIO.output(IN3, False)
        GPIO.output(IN4, True)
        pwmA.ChangeDutyCycle(speed)
        pwmB.ChangeDutyCycle(speed)
    else:
        print(f"[MOTOR] LEFT speed={speed}")


def motor_right(speed=50):
    """우회전"""
    if USE_GPIO:
        GPIO.output(IN1, False)
        GPIO.output(IN2, True)
        GPIO.output(IN3, True)
        GPIO.output(IN4, False)
        pwmA.ChangeDutyCycle(speed)
        pwmB.ChangeDutyCycle(speed)
    else:
        print(f"[MOTOR] RIGHT speed={speed}")


def motor_stop():
    """정지"""
    if USE_GPIO:
        GPIO.output(IN1, False)
        GPIO.output(IN2, False)
        GPIO.output(IN3, False)
        GPIO.output(IN4, False)
        pwmA.ChangeDutyCycle(0)
        pwmB.ChangeDutyCycle(0)
    else:
        print("[MOTOR] STOP")


def open_camera():
    """카메라 열기"""
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        return cap
    try:
        from picamera2 import Picamera2
        picam2 = Picamera2()
        picam2.configure(picam2.create_preview_configuration(main={"format": "RGB888"}))
        picam2.start()

        class PicamWrap:
            def read(self):
                frame = picam2.capture_array()
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                return True, frame

            def release(self):
                picam2.stop()

        return PicamWrap()
    except Exception as e:
        raise RuntimeError("Camera open failed: " + str(e))


def detect_yellow_line(roi, lower_yellow, upper_yellow, min_pixels=100):
    """
    ROI에서 노란색 라인 감지 (HSV 색공간 사용)

    Args:
        roi: ROI 이미지
        lower_yellow: 노란색 하한값 (HSV)
        upper_yellow: 노란색 상한값 (HSV)
        min_pixels: 라인으로 판단할 최소 픽셀 수

    Returns:
        bool: 라인 감지 여부
        int: 라인 픽셀 수
        binary: 이진화 이미지
    """
    # BGR을 HSV로 변환
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # 노란색 마스크 생성
    mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

    # 노이즈 제거
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.erode(mask, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=2)

    # 라인 픽셀 수 계산
    line_pixels = cv2.countNonZero(mask)
    has_line = line_pixels > min_pixels

    return has_line, line_pixels, mask


def decide_command_improved(frame, roi_height_ratio=0.4, roi_width_ratio=0.35,
                           lower_yellow=np.array([20, 100, 100]),
                           upper_yellow=np.array([30, 255, 255]),
                           min_pixels=150):
    """
    개선된 제어 로직 - 노란색 라인을 벗어나지 않고 따라가기

    Args:
        frame: 입력 프레임
        roi_height_ratio: ROI 높이 비율
        roi_width_ratio: 좌우 ROI 너비 비율
        lower_yellow: 노란색 하한값
        upper_yellow: 노란색 상한값
        min_pixels: 최소 픽셀 수

    Returns:
        command, debug_info
    """
    h, w = frame.shape[:2]

    # ROI 영역 계산
    roi_h = int(h * roi_height_ratio)
    roi_w = int(w * roi_width_ratio)
    roi_y = h - roi_h

    # 좌측, 중앙, 우측 ROI 설정
    left_roi = frame[roi_y:h, 0:roi_w]
    center_x1 = (w - roi_w) // 2
    center_x2 = center_x1 + roi_w
    center_roi = frame[roi_y:h, center_x1:center_x2]
    right_roi = frame[roi_y:h, w-roi_w:w]

    # 각 ROI에서 노란색 라인 감지
    left_has_line, left_pixels, left_binary = detect_yellow_line(
        left_roi, lower_yellow, upper_yellow, min_pixels
    )
    center_has_line, center_pixels, center_binary = detect_yellow_line(
        center_roi, lower_yellow, upper_yellow, min_pixels
    )
    right_has_line, right_pixels, right_binary = detect_yellow_line(
        right_roi, lower_yellow, upper_yellow, min_pixels
    )

    # 개선된 제어 로직
    # 우선순위: 중앙 라인 > 좌우 균형 > 한쪽만 있을 때 복귀

    if center_has_line:
        # 중앙에 라인이 있으면 직진 (트랙 중앙 유지)
        command = "forward"

    elif left_has_line and right_has_line:
        # 좌우 모두 라인 있으면 직진 (두 라인 사이)
        # 픽셀 수 차이로 미세 조정
        pixel_diff = left_pixels - right_pixels
        if abs(pixel_diff) < 100:
            command = "forward"
        elif pixel_diff > 0:
            # 좌측 라인이 더 많이 보임 → 우회전으로 중앙 복귀
            command = "slight_right"
        else:
            # 우측 라인이 더 많이 보임 → 좌회전으로 중앙 복귀
            command = "slight_left"

    elif left_has_line and not right_has_line:
        # 좌측만 라인 있음 → 우회전 (라인 안쪽으로)
        command = "right"

    elif not left_has_line and right_has_line:
        # 우측만 라인 있음 → 좌회전 (라인 안쪽으로)
        command = "left"

    else:
        # 라인이 전혀 안 보임 → 정지 후 천천히 회전하며 라인 찾기
        command = "search"

    # 디버그 정보
    debug_info = {
        "left_has_line": left_has_line,
        "center_has_line": center_has_line,
        "right_has_line": right_has_line,
        "left_pixels": left_pixels,
        "center_pixels": center_pixels,
        "right_pixels": right_pixels,
        "roi_coords": {
            "left": (0, roi_y, roi_w, h),
            "center": (center_x1, roi_y, center_x2, h),
            "right": (w-roi_w, roi_y, w, h)
        }
    }

    return command, left_binary, center_binary, right_binary, debug_info


def draw_debug_overlay_improved(frame, debug_info, command,
                               left_binary, center_binary, right_binary):
    """개선된 디버그 오버레이"""

    # ROI 좌표
    left_coords = debug_info["roi_coords"]["left"]
    center_coords = debug_info["roi_coords"]["center"]
    right_coords = debug_info["roi_coords"]["right"]

    # 감지된 노란색 라인을 초록색으로 표시 (더 명확하게)
    # 좌측
    left_y1, left_y2 = left_coords[1], left_coords[3]
    left_x1, left_x2 = left_coords[0], left_coords[2]
    frame[left_y1:left_y2, left_x1:left_x2][left_binary > 0] = [0, 255, 0]

    # 중앙
    center_y1, center_y2 = center_coords[1], center_coords[3]
    center_x1, center_x2 = center_coords[0], center_coords[2]
    frame[center_y1:center_y2, center_x1:center_x2][center_binary > 0] = [0, 255, 0]

    # 우측
    right_y1, right_y2 = right_coords[1], right_coords[3]
    right_x1, right_x2 = right_coords[0], right_coords[2]
    frame[right_y1:right_y2, right_x1:right_x2][right_binary > 0] = [0, 255, 0]

    # ROI 박스 그리기 (라인 있음=파란색, 없음=빨강)
    left_color = (255, 0, 0) if debug_info["left_has_line"] else (0, 0, 255)
    cv2.rectangle(frame, (left_coords[0], left_coords[1]),
                  (left_coords[2], left_coords[3]), left_color, 2)

    center_color = (255, 0, 0) if debug_info["center_has_line"] else (0, 0, 255)
    cv2.rectangle(frame, (center_coords[0], center_coords[1]),
                  (center_coords[2], center_coords[3]), center_color, 3)

    right_color = (255, 0, 0) if debug_info["right_has_line"] else (0, 0, 255)
    cv2.rectangle(frame, (right_coords[0], right_coords[1]),
                  (right_coords[2], right_coords[3]), right_color, 2)

    # 텍스트 정보
    y_offset = 30
    # 명령어 표시
    command_text = command.upper().replace("_", " ")
    cv2.putText(frame, f"Command: {command_text}", (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    y_offset += 30
    cv2.putText(frame, f"Left: {debug_info['left_pixels']}px", (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, left_color, 2)

    y_offset += 25
    cv2.putText(frame, f"Center: {debug_info['center_pixels']}px", (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, center_color, 2)

    y_offset += 25
    cv2.putText(frame, f"Right: {debug_info['right_pixels']}px", (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, right_color, 2)

    return frame


def main():
    """메인 루프"""
    cap = open_camera()
    print("[INFO] Improved Dual ROI Line Tracer - 노란색 라인 전용")
    print("[INFO] q/ESC: 종료")
    print("[INFO] 1/2: H_min 조정 (노란색 범위)")
    print("[INFO] 3/4: H_max 조정")
    print("[INFO] 5/6: S_min 조정 (채도)")
    print("[INFO] 7/8: 최소 픽셀 수 조정")
    print("[INFO] s: 현재 설정 출력")

    # 초기 파라미터 (노란색 라인용)
    h_min, h_max = 20, 30
    s_min, s_max = 100, 255
    v_min, v_max = 100, 255
    min_pixels = 150
    roi_height_ratio = 0.4
    roi_width_ratio = 0.35

    # 라인 검색 모드 변수
    search_direction = "right"  # 라인 없을 때 회전 방향
    search_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # HSV 범위 설정
            lower_yellow = np.array([h_min, s_min, v_min])
            upper_yellow = np.array([h_max, s_max, v_max])

            # 명령 결정
            command, left_binary, center_binary, right_binary, debug_info = decide_command_improved(
                frame, roi_height_ratio, roi_width_ratio,
                lower_yellow, upper_yellow, min_pixels
            )

            # 모터 제어
            if command == "forward":
                motor_forward(65)
                search_count = 0

            elif command == "slight_left":
                # 미세 좌회전
                motor_left(40)
                search_count = 0

            elif command == "slight_right":
                # 미세 우회전
                motor_right(40)
                search_count = 0

            elif command == "left":
                motor_left(50)
                search_direction = "left"
                search_count = 0

            elif command == "right":
                motor_right(50)
                search_direction = "right"
                search_count = 0

            elif command == "search":
                # 라인 찾기 모드
                search_count += 1
                if search_count < 10:
                    motor_stop()  # 잠시 정지
                elif search_count < 50:
                    # 마지막 방향으로 천천히 회전
                    if search_direction == "left":
                        motor_left(35)
                    else:
                        motor_right(35)
                else:
                    # 너무 오래 못 찾으면 반대 방향 시도
                    search_direction = "left" if search_direction == "right" else "right"
                    search_count = 10

            else:
                motor_stop()

            # 디버그 오버레이
            frame = draw_debug_overlay_improved(
                frame, debug_info, command,
                left_binary, center_binary, right_binary
            )

            # 화면 출력
            cv2.imshow("Line Tracer", frame)
            cv2.imshow("Left ROI", left_binary)
            cv2.imshow("Center ROI", center_binary)
            cv2.imshow("Right ROI", right_binary)

            # 키 입력 처리
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q')):
                motor_stop()
                break
            elif key == ord('1'):
                h_min = max(0, h_min - 2)
                print(f"[PARAM] H_min: {h_min}")
            elif key == ord('2'):
                h_min = min(179, h_min + 2)
                print(f"[PARAM] H_min: {h_min}")
            elif key == ord('3'):
                h_max = max(h_min, h_max - 2)
                print(f"[PARAM] H_max: {h_max}")
            elif key == ord('4'):
                h_max = min(179, h_max + 2)
                print(f"[PARAM] H_max: {h_max}")
            elif key == ord('5'):
                s_min = max(0, s_min - 10)
                print(f"[PARAM] S_min: {s_min}")
            elif key == ord('6'):
                s_min = min(255, s_min + 10)
                print(f"[PARAM] S_min: {s_min}")
            elif key == ord('7'):
                min_pixels = max(50, min_pixels - 50)
                print(f"[PARAM] min_pixels: {min_pixels}")
            elif key == ord('8'):
                min_pixels += 50
                print(f"[PARAM] min_pixels: {min_pixels}")
            elif key == ord('s'):
                print(f"\n=== 현재 설정 ===")
                print(f"lower_yellow = np.array([{h_min}, {s_min}, {v_min}])")
                print(f"upper_yellow = np.array([{h_max}, {s_max}, {v_max}])")
                print(f"min_pixels = {min_pixels}")
                print(f"==================\n")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        motor_stop()
        if USE_GPIO:
            GPIO.cleanup()
        print("[INFO] 프로그램 종료")


if __name__ == "__main__":
    main()
