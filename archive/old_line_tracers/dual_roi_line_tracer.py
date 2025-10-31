"""
Dual ROI Line Tracer
학습 없이 좌우 하단 ROI를 사용한 라인 트레이싱
라인이 사라진 쪽으로 회전하여 라인을 다시 찾는 로직
"""
import cv2

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
    """카메라 열기 (OpenCV 또는 PiCamera)"""
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


def detect_line_in_roi(roi, thresh=150, min_pixels=100):
    """
    ROI에서 라인 감지

    Args:
        roi: ROI 이미지
        thresh: 이진화 임계값
        min_pixels: 라인으로 판단할 최소 픽셀 수

    Returns:
        bool: 라인 감지 여부
        int: 라인 픽셀 수
    """
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blur, thresh, 255, cv2.THRESH_BINARY_INV)

    # 라인 픽셀 수 계산
    line_pixels = cv2.countNonZero(binary)
    has_line = line_pixels > min_pixels

    return has_line, line_pixels, binary


def decide_command(frame, roi_height_ratio=0.3, roi_width_ratio=0.3, thresh=150, min_pixels=100):
    """
    좌우 하단 ROI를 기반으로 제어 명령 결정

    Args:
        frame: 입력 프레임
        roi_height_ratio: ROI 높이 비율 (화면 하단 기준)
        roi_width_ratio: 좌우 ROI 너비 비율 (화면 너비 기준)
        thresh: 이진화 임계값
        min_pixels: 라인 감지 최소 픽셀 수

    Returns:
        command: 제어 명령 ("forward", "left", "right", "stop")
        left_roi: 좌측 ROI 이미지
        right_roi: 우측 ROI 이미지
        left_binary: 좌측 이진화 이미지
        right_binary: 우측 이진화 이미지
        debug_info: 디버그 정보
    """
    h, w = frame.shape[:2]

    # ROI 영역 계산
    roi_h = int(h * roi_height_ratio)
    roi_w = int(w * roi_width_ratio)
    roi_y = h - roi_h  # 하단 시작점

    # 좌측 하단 ROI
    left_roi = frame[roi_y:h, 0:roi_w]
    # 우측 하단 ROI
    right_roi = frame[roi_y:h, w-roi_w:w]

    # 각 ROI에서 라인 감지
    left_has_line, left_pixels, left_binary = detect_line_in_roi(left_roi, thresh, min_pixels)
    right_has_line, right_pixels, right_binary = detect_line_in_roi(right_roi, thresh, min_pixels)

    # 제어 로직
    if left_has_line and right_has_line:
        # 좌우 모두 라인 있음 → 직진
        command = "forward"
    elif not left_has_line and right_has_line:
        # 좌측만 라인 없음 → 좌측으로 회전 (라인을 찾기 위해)
        command = "left"
    elif left_has_line and not right_has_line:
        # 우측만 라인 없음 → 우측으로 회전 (라인을 찾기 위해)
        command = "right"
    else:
        # 좌우 모두 라인 없음 → 정지
        command = "stop"

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


def draw_debug_overlay(frame, debug_info, command, left_binary, right_binary):
    """
    디버그 정보를 프레임에 오버레이

    Args:
        frame: 입력 프레임
        debug_info: 디버그 정보 딕셔너리
        command: 현재 제어 명령
        left_binary: 좌측 이진화 이미지
        right_binary: 우측 이진화 이미지
    """

    # ROI 영역 표시
    left_coords = debug_info["roi_coords"]["left"]
    right_coords = debug_info["roi_coords"]["right"]

    # 감지된 라인을 노란색으로 표시
    # 좌측 라인
    left_y1, left_y2 = left_coords[1], left_coords[3]
    left_x1, left_x2 = left_coords[0], left_coords[2]
    left_colored = cv2.cvtColor(left_binary, cv2.COLOR_GRAY2BGR)
    yellow_mask_left = cv2.inRange(left_colored, (200, 200, 200), (255, 255, 255))
    frame[left_y1:left_y2, left_x1:left_x2][yellow_mask_left > 0] = [0, 255, 255]  # 노란색 (BGR)

    # 우측 라인
    right_y1, right_y2 = right_coords[1], right_coords[3]
    right_x1, right_x2 = right_coords[0], right_coords[2]
    right_colored = cv2.cvtColor(right_binary, cv2.COLOR_GRAY2BGR)
    yellow_mask_right = cv2.inRange(right_colored, (200, 200, 200), (255, 255, 255))
    frame[right_y1:right_y2, right_x1:right_x2][yellow_mask_right > 0] = [0, 255, 255]  # 노란색 (BGR)

    # ROI 박스 (녹색=라인있음, 빨강=라인없음)
    left_color = (0, 255, 0) if debug_info["left_has_line"] else (0, 0, 255)
    cv2.rectangle(frame, (left_coords[0], left_coords[1]),
                  (left_coords[2], left_coords[3]), left_color, 2)

    # 우측 ROI 박스
    right_color = (0, 255, 0) if debug_info["right_has_line"] else (0, 0, 255)
    cv2.rectangle(frame, (right_coords[0], right_coords[1]),
                  (right_coords[2], right_coords[3]), right_color, 2)

    # 텍스트 정보
    y_offset = 30
    cv2.putText(frame, f"Command: {command.upper()}", (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    y_offset += 30
    cv2.putText(frame, f"Left: {debug_info['left_pixels']}px {'[LINE]' if debug_info['left_has_line'] else '[NONE]'}",
                (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, left_color, 2)

    y_offset += 25
    cv2.putText(frame, f"Right: {debug_info['right_pixels']}px {'[LINE]' if debug_info['right_has_line'] else '[NONE]'}",
                (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, right_color, 2)

    return frame


def main():
    """메인 루프"""
    cap = open_camera()
    print("[INFO] Dual ROI Line Tracer")
    print("[INFO] q/ESC: 종료")
    print("[INFO] 1/2: 임계값 조정 (어둡게/밝게)")
    print("[INFO] 3/4: ROI 높이 조정 (증가/감소)")
    print("[INFO] 5/6: ROI 너비 조정 (증가/감소)")
    print("[INFO] 7/8: 최소 픽셀 수 조정 (증가/감소)")

    # 초기 파라미터
    thresh = 150
    roi_height_ratio = 0.3
    roi_width_ratio = 0.3
    min_pixels = 100

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 명령 결정
            command, _, _, left_binary, right_binary, debug_info = decide_command(
                frame, roi_height_ratio, roi_width_ratio, thresh, min_pixels
            )

            # 모터 제어
            if command == "forward":
                motor_forward(65)
            elif command == "left":
                motor_left(50)
            elif command == "right":
                motor_right(50)
            else:
                motor_stop()

            # 디버그 오버레이
            frame = draw_debug_overlay(frame, debug_info, command, left_binary, right_binary)

            # 화면 출력
            cv2.imshow("Line Tracer", frame)
            cv2.imshow("Left ROI", left_binary)
            cv2.imshow("Right ROI", right_binary)

            # 키 입력 처리
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q')):  # ESC, q
                motor_stop()
                break
            elif key == ord('1'):
                thresh = max(60, thresh - 5)
                print(f"[PARAM] thresh: {thresh}")
            elif key == ord('2'):
                thresh = min(220, thresh + 5)
                print(f"[PARAM] thresh: {thresh}")
            elif key == ord('3'):
                roi_height_ratio = min(0.6, roi_height_ratio + 0.05)
                print(f"[PARAM] roi_height_ratio: {roi_height_ratio:.2f}")
            elif key == ord('4'):
                roi_height_ratio = max(0.1, roi_height_ratio - 0.05)
                print(f"[PARAM] roi_height_ratio: {roi_height_ratio:.2f}")
            elif key == ord('5'):
                roi_width_ratio = min(0.5, roi_width_ratio + 0.05)
                print(f"[PARAM] roi_width_ratio: {roi_width_ratio:.2f}")
            elif key == ord('6'):
                roi_width_ratio = max(0.1, roi_width_ratio - 0.05)
                print(f"[PARAM] roi_width_ratio: {roi_width_ratio:.2f}")
            elif key == ord('7'):
                min_pixels += 50
                print(f"[PARAM] min_pixels: {min_pixels}")
            elif key == ord('8'):
                min_pixels = max(50, min_pixels - 50)
                print(f"[PARAM] min_pixels: {min_pixels}")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        motor_stop()
        if USE_GPIO:
            GPIO.cleanup()
        print("[INFO] 프로그램 종료")


if __name__ == "__main__":
    main()
