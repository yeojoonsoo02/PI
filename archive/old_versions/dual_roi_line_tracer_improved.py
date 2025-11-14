"""
Improved Dual ROI Line Tracer - 노란색 라인 전용
트랙을 벗어나지 않고 노란색 라인을 따라가는 개선된 로직
+ 갈림길 감지 및 키보드 제어 기능
"""
import cv2
import numpy as np
import time

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
    """카메라 열기 - 라즈베리파이 카메라 우선"""
    # 방법 1: Picamera2 먼저 시도 (라즈베리파이 카메라)
    try:
        from picamera2 import Picamera2
        print("[INFO] Trying Picamera2...")
        picam2 = Picamera2()

        # 해상도를 낮춰서 메모리 부담 감소
        config = picam2.create_preview_configuration(
            main={"format": "RGB888", "size": (640, 480)}
        )
        picam2.configure(config)
        picam2.start()

        print("[INFO] Picamera2 initialized successfully!")

        class PicamWrap:
            def read(self):
                frame = picam2.capture_array()
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                return True, frame

            def release(self):
                picam2.stop()

        return PicamWrap()
    except Exception as e:
        print(f"[WARN] Picamera2 failed: {e}")

    # 방법 2: OpenCV VideoCapture 시도 (USB 카메라)
    try:
        print("[INFO] Trying OpenCV VideoCapture...")
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)  # V4L2 백엔드 명시

        # 해상도 설정
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

        # 버퍼 크기 줄이기
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if cap.isOpened():
            print("[INFO] OpenCV VideoCapture initialized successfully!")
            return cap
        else:
            cap.release()
    except Exception as e:
        print(f"[WARN] OpenCV VideoCapture failed: {e}")

    # 방법 3: GStreamer 파이프라인 시도
    try:
        print("[INFO] Trying GStreamer pipeline...")
        gst_pipeline = (
            "v4l2src device=/dev/video0 ! "
            "video/x-raw,width=640,height=480,framerate=30/1 ! "
            "videoconvert ! appsink"
        )
        cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
        if cap.isOpened():
            print("[INFO] GStreamer pipeline initialized successfully!")
            return cap
    except Exception as e:
        print(f"[WARN] GStreamer failed: {e}")

    raise RuntimeError("All camera initialization methods failed. Please check camera connection.")


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


def detect_junction(left_has_line, center_has_line, right_has_line,
                   left_pixels, center_pixels, right_pixels,
                   junction_threshold=200):
    """
    갈림길 감지 함수

    Args:
        left_has_line, center_has_line, right_has_line: 각 ROI의 라인 감지 여부
        left_pixels, center_pixels, right_pixels: 각 ROI의 라인 픽셀 수
        junction_threshold: 갈림길로 판단할 최소 픽셀 수

    Returns:
        junction_type: "none", "left_right", "left_center", "right_center", "all"
        available_directions: 가능한 방향 리스트
    """
    # 갈림길 타입 판단
    junction_type = "none"
    available_directions = []

    # 좌우 양쪽 모두 라인이 있고, 충분한 픽셀 수가 있으면
    if left_has_line and right_has_line and \
       left_pixels >= junction_threshold and right_pixels >= junction_threshold:

        if center_has_line and center_pixels >= junction_threshold:
            # 좌/중앙/우 모두 라인 있음 → T자 또는 십자 갈림길
            junction_type = "all"
            available_directions = ["left", "forward", "right"]
        else:
            # 좌/우만 라인 있음 → 좌우 갈림길
            junction_type = "left_right"
            available_directions = ["left", "right"]

    # 좌측과 중앙만 라인이 있는 경우
    elif left_has_line and center_has_line and not right_has_line and \
         left_pixels >= junction_threshold and center_pixels >= junction_threshold:
        junction_type = "left_center"
        available_directions = ["left", "forward"]

    # 우측과 중앙만 라인이 있는 경우
    elif right_has_line and center_has_line and not left_has_line and \
         right_pixels >= junction_threshold and center_pixels >= junction_threshold:
        junction_type = "right_center"
        available_directions = ["right", "forward"]

    return junction_type, available_directions


def decide_command_improved(frame, roi_height_ratio=0.4, roi_width_ratio=0.35,
                           lower_yellow=np.array([20, 100, 100]),
                           upper_yellow=np.array([30, 255, 255]),
                           min_pixels=150,
                           junction_threshold=200):
    """
    개선된 제어 로직 - 노란색 라인을 벗어나지 않고 따라가기 + 갈림길 감지

    Args:
        frame: 입력 프레임
        roi_height_ratio: ROI 높이 비율
        roi_width_ratio: 좌우 ROI 너비 비율
        lower_yellow: 노란색 하한값
        upper_yellow: 노란색 상한값
        min_pixels: 최소 픽셀 수
        junction_threshold: 갈림길 판단 임계값

    Returns:
        command, debug_info, junction_info
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

    # 갈림길 감지
    junction_type, available_directions = detect_junction(
        left_has_line, center_has_line, right_has_line,
        left_pixels, center_pixels, right_pixels,
        junction_threshold
    )

    # 갈림길 정보
    junction_info = {
        "is_junction": junction_type != "none",
        "junction_type": junction_type,
        "available_directions": available_directions
    }

    # 갈림길이면 정지
    if junction_info["is_junction"]:
        command = "junction"

    # 개선된 제어 로직 (갈림길 아닐 때)
    elif center_has_line:
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

    return command, left_binary, center_binary, right_binary, debug_info, junction_info


def motor_backward(speed=60):
    """후진"""
    if USE_GPIO:
        GPIO.output(IN1, False)
        GPIO.output(IN2, True)
        GPIO.output(IN3, False)
        GPIO.output(IN4, True)
        pwmA.ChangeDutyCycle(speed)
        pwmB.ChangeDutyCycle(speed)
    else:
        print(f"[MOTOR] BACKWARD speed={speed}")


def draw_debug_overlay_improved(frame, debug_info, command,
                               left_binary, center_binary, right_binary,
                               search_count=0, rotation_angle=0,
                               junction_info=None):
    """개선된 디버그 오버레이 (갈림길 정보 포함)"""

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

    # 갈림길 정보 표시
    if junction_info and junction_info["is_junction"]:
        junction_color = (255, 0, 255)  # 마젠타
        cv2.putText(frame, f"JUNCTION DETECTED!", (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, junction_color, 3)
        y_offset += 35

        directions_text = " | ".join(junction_info["available_directions"])
        cv2.putText(frame, f"Available: {directions_text}", (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, junction_color, 2)
        y_offset += 30
        cv2.putText(frame, f"Press Arrow Keys to Choose Direction", (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    # 명령어 표시 (검색 모드일 때 특별 표시)
    elif command == "search":
        command_color = (0, 165, 255)  # 주황색
        cv2.putText(frame, f"SEARCHING LINE...", (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, command_color, 2)
        y_offset += 30
        cv2.putText(frame, f"Rotation: ~{rotation_angle}deg", (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, command_color, 2)
    else:
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
    print("[INFO] Improved Dual ROI Line Tracer - 노란색 라인 전용 + 갈림길 감지")
    print("[INFO] q/ESC: 종료")
    print("[INFO] Arrow Keys: 갈림길에서 방향 선택 (↑↓←→)")
    print("[INFO] 1/2: H_min 조정 (노란색 범위)")
    print("[INFO] 3/4: H_max 조정")
    print("[INFO] 5/6: S_min 조정 (채도)")
    print("[INFO] 7/8: 최소 픽셀 수 조정")
    print("[INFO] 9/0: 갈림길 임계값 조정")
    print("[INFO] s: 현재 설정 출력")

    # 초기 파라미터 (노란색 라인용)
    h_min, h_max = 20, 30
    s_min, s_max = 100, 255
    v_min, v_max = 100, 255
    min_pixels = 150
    junction_threshold = 200
    roi_height_ratio = 0.4
    roi_width_ratio = 0.35

    # 라인 검색 모드 변수
    search_direction = "right"  # 라인 없을 때 회전 방향
    search_count = 0
    last_seen_direction = "center"  # 마지막으로 라인이 보인 방향
    rotation_angle = 0  # 현재 회전 각도 (추정)
    max_rotation_angle = 180  # 최대 회전 각도

    # 갈림길 모드 변수
    at_junction = False
    junction_start_time = 0
    selected_direction = None

    # 라인 이탈 감지 변수
    line_lost_count = 0  # 라인을 못 본 연속 프레임 수
    line_lost_threshold = 30  # 이탈로 판단할 프레임 수 (약 1초)
    backing_up = False  # 후진 중 여부
    backup_count = 0  # 후진 프레임 수

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # HSV 범위 설정
            lower_yellow = np.array([h_min, s_min, v_min])
            upper_yellow = np.array([h_max, s_max, v_max])

            # 명령 결정
            command, left_binary, center_binary, right_binary, debug_info, junction_info = decide_command_improved(
                frame, roi_height_ratio, roi_width_ratio,
                lower_yellow, upper_yellow, min_pixels, junction_threshold
            )

            # 라인 이탈 감지 (검색 모드가 아닐 때만)
            has_any_line = debug_info["left_has_line"] or debug_info["center_has_line"] or debug_info["right_has_line"]

            if command == "search" and not backing_up:
                line_lost_count += 1
                if line_lost_count >= line_lost_threshold:
                    # 라인 이탈 판정 - 후진 시작
                    backing_up = True
                    backup_count = 0
                    print(f"[WARNING] Line lost! Starting backup...")
            else:
                # 라인을 찾았거나 갈림길이면 카운터 리셋
                line_lost_count = 0

            # 모터 제어
            if backing_up:
                # 후진 모드
                backup_count += 1
                motor_backward(60)
                print(f"[BACKUP] Backing up... ({backup_count}/60)")

                if backup_count >= 60:  # 약 2초 후진
                    backing_up = False
                    backup_count = 0
                    line_lost_count = 0
                    search_count = 0
                    print("[BACKUP] Backup complete. Resuming search...")

            elif command == "junction":
                # 갈림길 감지 - 정지 후 키보드 입력 대기
                motor_stop()

                if not at_junction:
                    at_junction = True
                    junction_start_time = time.time()
                    print(f"[JUNCTION] Junction detected! Available: {junction_info['available_directions']}")
                    print("[JUNCTION] Press Arrow Keys: ← (left), ↑ (forward), → (right)")

                # 갈림길에서 대기 중 - 키보드 입력은 아래에서 처리

            elif command == "forward":
                motor_forward(65)
                search_count = 0
                rotation_angle = 0
                last_seen_direction = "center"
                at_junction = False

            elif command == "slight_left":
                # 미세 좌회전
                motor_left(40)
                search_count = 0
                rotation_angle = 0
                last_seen_direction = "center"
                at_junction = False

            elif command == "slight_right":
                # 미세 우회전
                motor_right(40)
                search_count = 0
                rotation_angle = 0
                last_seen_direction = "center"
                at_junction = False

            elif command == "left":
                motor_left(50)
                search_direction = "left"
                search_count = 0
                rotation_angle = 0
                last_seen_direction = "left"
                at_junction = False

            elif command == "right":
                motor_right(50)
                search_direction = "right"
                search_count = 0
                rotation_angle = 0
                last_seen_direction = "right"
                at_junction = False

            elif command == "search":
                # 개선된 라인 찾기 모드
                search_count += 1

                if search_count < 5:
                    # 1단계: 정지하고 주변 확인
                    motor_stop()
                    print(f"[SEARCH] 정지 중... ({search_count}/5)")

                elif search_count < 60:
                    # 2단계: 마지막 본 방향으로 제자리 회전
                    rotation_angle += 3  # 약 3도씩 회전 (추정)

                    # 마지막에 본 방향의 반대편으로 먼저 회전
                    if last_seen_direction == "left":
                        motor_right(40)  # 우회전
                        print(f"[SEARCH] 우회전 검색 중... (각도: ~{rotation_angle}°)")
                    elif last_seen_direction == "right":
                        motor_left(40)   # 좌회전
                        print(f"[SEARCH] 좌회전 검색 중... (각도: ~{rotation_angle}°)")
                    else:  # center 또는 기타
                        # 기본적으로 우회전
                        motor_right(40)
                        print(f"[SEARCH] 우회전 검색 중... (각도: ~{rotation_angle}°)")

                elif search_count < 120:
                    # 3단계: 반대 방향으로 회전
                    rotation_angle += 3

                    if last_seen_direction == "left":
                        motor_left(40)   # 좌회전
                        print(f"[SEARCH] 반대 방향(좌) 검색 중... (각도: ~{rotation_angle}°)")
                    elif last_seen_direction == "right":
                        motor_right(40)  # 우회전
                        print(f"[SEARCH] 반대 방향(우) 검색 중... (각도: ~{rotation_angle}°)")
                    else:
                        motor_left(40)
                        print(f"[SEARCH] 반대 방향(좌) 검색 중... (각도: ~{rotation_angle}°)")

                elif search_count < 180:
                    # 4단계: 360도 완전 회전
                    rotation_angle += 3
                    motor_right(35)
                    print(f"[SEARCH] 360도 회전 검색 중... (각도: ~{rotation_angle}°)")

                else:
                    # 5단계: 라인을 찾지 못함 - 정지
                    motor_stop()
                    print("[SEARCH] 라인을 찾지 못했습니다. 정지합니다.")
                    if search_count >= 300:  # 5초 정도 정지 후 재시도
                        search_count = 0
                        rotation_angle = 0

            else:
                motor_stop()

            # 디버그 오버레이
            frame = draw_debug_overlay_improved(
                frame, debug_info, command,
                left_binary, center_binary, right_binary,
                search_count, rotation_angle, junction_info
            )

            # 화면 출력
            cv2.imshow("Line Tracer", frame)
            cv2.imshow("Left ROI", left_binary)
            cv2.imshow("Center ROI", center_binary)
            cv2.imshow("Right ROI", right_binary)

            # 키 입력 처리
            key = cv2.waitKey(1) & 0xFF

            # 갈림길에서 방향키 입력 처리
            if at_junction and key != 255:
                if key == 82 or key == ord('w'):  # 위쪽 화살표 또는 'w' (forward)
                    if "forward" in junction_info["available_directions"]:
                        print("[JUNCTION] Selected: FORWARD")
                        selected_direction = "forward"
                        motor_forward(65)
                        time.sleep(1.0)  # 1초 동안 직진
                        at_junction = False
                    else:
                        print("[JUNCTION] Forward not available!")

                elif key == 81 or key == ord('a'):  # 왼쪽 화살표 또는 'a' (left)
                    if "left" in junction_info["available_directions"]:
                        print("[JUNCTION] Selected: LEFT")
                        selected_direction = "left"
                        motor_left(50)
                        time.sleep(0.8)  # 0.8초 동안 좌회전
                        at_junction = False
                    else:
                        print("[JUNCTION] Left not available!")

                elif key == 83 or key == ord('d'):  # 오른쪽 화살표 또는 'd' (right)
                    if "right" in junction_info["available_directions"]:
                        print("[JUNCTION] Selected: RIGHT")
                        selected_direction = "right"
                        motor_right(50)
                        time.sleep(0.8)  # 0.8초 동안 우회전
                        at_junction = False
                    else:
                        print("[JUNCTION] Right not available!")

            # 일반 키 입력 처리
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
            elif key == ord('9'):
                junction_threshold = max(100, junction_threshold - 50)
                print(f"[PARAM] junction_threshold: {junction_threshold}")
            elif key == ord('0'):
                junction_threshold += 50
                print(f"[PARAM] junction_threshold: {junction_threshold}")
            elif key == ord('s'):
                print(f"\n=== 현재 설정 ===")
                print(f"lower_yellow = np.array([{h_min}, {s_min}, {v_min}])")
                print(f"upper_yellow = np.array([{h_max}, {s_max}, {v_max}])")
                print(f"min_pixels = {min_pixels}")
                print(f"junction_threshold = {junction_threshold}")
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
