"""
Improved Dual ROI Line Tracer - 헤드리스 모드 (SSH용)
디스플레이 없이 실행 가능한 버전
"""
import cv2
import numpy as np
import time
import os

# OpenCV 헤드리스 모드 설정
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

USE_GPIO = True  # SSH 실행시 True로 설정
if USE_GPIO:
    try:
        import RPi.GPIO as GPIO
        IN1, IN2, IN3, IN4, ENA, ENB = 17, 18, 22, 23, 24, 25
        GPIO.setmode(GPIO.BCM)
        for p in (IN1, IN2, IN3, IN4, ENA, ENB):
            GPIO.setup(p, GPIO.OUT)
        pwmA = GPIO.PWM(ENA, 1000)
        pwmA.start(0)
        pwmB = GPIO.PWM(ENB, 1000)
        pwmB.start(0)
        print("[INFO] GPIO initialized successfully")
    except Exception as e:
        print(f"[WARN] GPIO initialization failed: {e}")
        USE_GPIO = False


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
    print("[MOTOR] STOP")


def motor_backward(speed=60):
    """후진"""
    if USE_GPIO:
        GPIO.output(IN1, False)
        GPIO.output(IN2, True)
        GPIO.output(IN3, False)
        GPIO.output(IN4, True)
        pwmA.ChangeDutyCycle(speed)
        pwmB.ChangeDutyCycle(speed)
    print(f"[MOTOR] BACKWARD speed={speed}")


def open_camera():
    """카메라 열기 - 헤드리스 모드"""
    try:
        from picamera2 import Picamera2
        print("[INFO] Trying Picamera2...")
        picam2 = Picamera2()

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
        print(f"[ERROR] Camera initialization failed: {e}")
        raise RuntimeError("Camera open failed")


def detect_yellow_line(roi, lower_yellow, upper_yellow, min_pixels=100):
    """ROI에서 노란색 라인 감지"""
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.erode(mask, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=2)

    line_pixels = cv2.countNonZero(mask)
    has_line = line_pixels > min_pixels

    return has_line, line_pixels, mask


def detect_junction(left_has_line, center_has_line, right_has_line,
                   left_pixels, center_pixels, right_pixels,
                   junction_threshold=200):
    """갈림길 감지"""
    junction_type = "none"
    available_directions = []

    if left_has_line and right_has_line and \
       left_pixels >= junction_threshold and right_pixels >= junction_threshold:
        if center_has_line and center_pixels >= junction_threshold:
            junction_type = "all"
            available_directions = ["left", "forward", "right"]
        else:
            junction_type = "left_right"
            available_directions = ["left", "right"]

    elif left_has_line and center_has_line and not right_has_line and \
         left_pixels >= junction_threshold and center_pixels >= junction_threshold:
        junction_type = "left_center"
        available_directions = ["left", "forward"]

    elif right_has_line and center_has_line and not left_has_line and \
         right_pixels >= junction_threshold and center_pixels >= junction_threshold:
        junction_type = "right_center"
        available_directions = ["right", "forward"]

    return junction_type, available_directions


def decide_command(frame, roi_height_ratio=0.4, roi_width_ratio=0.35,
                  lower_yellow=np.array([20, 100, 100]),
                  upper_yellow=np.array([30, 255, 255]),
                  min_pixels=150,
                  junction_threshold=200):
    """제어 명령 결정"""
    h, w = frame.shape[:2]

    roi_h = int(h * roi_height_ratio)
    roi_w = int(w * roi_width_ratio)
    roi_y = h - roi_h

    left_roi = frame[roi_y:h, 0:roi_w]
    center_x1 = (w - roi_w) // 2
    center_x2 = center_x1 + roi_w
    center_roi = frame[roi_y:h, center_x1:center_x2]
    right_roi = frame[roi_y:h, w-roi_w:w]

    left_has_line, left_pixels, _ = detect_yellow_line(
        left_roi, lower_yellow, upper_yellow, min_pixels
    )
    center_has_line, center_pixels, _ = detect_yellow_line(
        center_roi, lower_yellow, upper_yellow, min_pixels
    )
    right_has_line, right_pixels, _ = detect_yellow_line(
        right_roi, lower_yellow, upper_yellow, min_pixels
    )

    junction_type, available_directions = detect_junction(
        left_has_line, center_has_line, right_has_line,
        left_pixels, center_pixels, right_pixels,
        junction_threshold
    )

    junction_info = {
        "is_junction": junction_type != "none",
        "junction_type": junction_type,
        "available_directions": available_directions
    }

    if junction_info["is_junction"]:
        command = "junction"
    elif center_has_line:
        command = "forward"
    elif left_has_line and right_has_line:
        pixel_diff = left_pixels - right_pixels
        if abs(pixel_diff) < 100:
            command = "forward"
        elif pixel_diff > 0:
            command = "slight_right"
        else:
            command = "slight_left"
    elif left_has_line and not right_has_line:
        command = "right"
    elif not left_has_line and right_has_line:
        command = "left"
    else:
        command = "search"

    debug_info = {
        "left": left_pixels,
        "center": center_pixels,
        "right": right_pixels
    }

    return command, junction_info, debug_info


def main():
    """메인 루프 - 헤드리스 모드"""
    print("=" * 60)
    print(" Line Tracer - Headless Mode (SSH Compatible)")
    print("=" * 60)
    print("[INFO] Press Ctrl+C to stop")
    print()

    cap = open_camera()

    # 파라미터
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([30, 255, 255])
    min_pixels = 150
    junction_threshold = 200

    # 상태 변수
    search_count = 0
    last_seen_direction = "center"
    rotation_angle = 0
    line_lost_count = 0
    backing_up = False
    backup_count = 0
    at_junction = False

    # 자동 주행 모드 (갈림길에서는 기본 동작 선택)
    default_junction_action = "forward"  # 갈림길에서 기본 직진

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Failed to read frame")
                break

            command, junction_info, debug_info = decide_command(
                frame, 0.4, 0.35, lower_yellow, upper_yellow,
                min_pixels, junction_threshold
            )

            # 라인 이탈 감지
            if command == "search" and not backing_up:
                line_lost_count += 1
                if line_lost_count >= 30:
                    backing_up = True
                    backup_count = 0
                    print(f"[WARNING] Line lost! Starting backup...")
            else:
                line_lost_count = 0

            # 모터 제어
            if backing_up:
                backup_count += 1
                motor_backward(60)
                if backup_count >= 60:
                    backing_up = False
                    backup_count = 0
                    line_lost_count = 0
                    search_count = 0
                    print("[INFO] Backup complete")

            elif command == "junction":
                if not at_junction:
                    at_junction = True
                    print(f"[JUNCTION] Detected! Available: {junction_info['available_directions']}")
                    print(f"[JUNCTION] Auto-selecting: {default_junction_action}")

                # 자동으로 직진 선택
                if default_junction_action == "forward" and "forward" in junction_info["available_directions"]:
                    motor_forward(65)
                    time.sleep(1.0)
                    at_junction = False
                elif "left" in junction_info["available_directions"]:
                    motor_left(50)
                    time.sleep(0.8)
                    at_junction = False
                elif "right" in junction_info["available_directions"]:
                    motor_right(50)
                    time.sleep(0.8)
                    at_junction = False

            elif command == "forward":
                motor_forward(65)
                search_count = 0
                rotation_angle = 0
                last_seen_direction = "center"
                at_junction = False

            elif command == "slight_left":
                motor_left(40)
                search_count = 0
                rotation_angle = 0
                at_junction = False

            elif command == "slight_right":
                motor_right(40)
                search_count = 0
                rotation_angle = 0
                at_junction = False

            elif command == "left":
                motor_left(50)
                search_count = 0
                rotation_angle = 0
                last_seen_direction = "left"
                at_junction = False

            elif command == "right":
                motor_right(50)
                search_count = 0
                rotation_angle = 0
                last_seen_direction = "right"
                at_junction = False

            elif command == "search":
                search_count += 1
                if search_count < 5:
                    motor_stop()
                elif search_count < 60:
                    rotation_angle += 3
                    if last_seen_direction == "left":
                        motor_right(40)
                    elif last_seen_direction == "right":
                        motor_left(40)
                    else:
                        motor_right(40)
                elif search_count < 120:
                    rotation_angle += 3
                    if last_seen_direction == "left":
                        motor_left(40)
                    elif last_seen_direction == "right":
                        motor_right(40)
                    else:
                        motor_left(40)
                elif search_count < 180:
                    rotation_angle += 3
                    motor_right(35)
                else:
                    motor_stop()
                    if search_count >= 300:
                        search_count = 0
                        rotation_angle = 0

            # 상태 출력 (5초마다)
            if int(time.time()) % 5 == 0:
                print(f"[STATUS] L:{debug_info['left']:4d} C:{debug_info['center']:4d} R:{debug_info['right']:4d} | {command}")

            time.sleep(0.03)  # 약 30 FPS

    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user")
    finally:
        motor_stop()
        cap.release()
        if USE_GPIO:
            try:
                pwmA.stop()
                pwmB.stop()
                GPIO.cleanup()
            except:
                pass
        print("[INFO] Program terminated")


if __name__ == "__main__":
    main()
