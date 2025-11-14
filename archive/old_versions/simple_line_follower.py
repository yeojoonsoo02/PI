"""
Simple Yellow Line Follower - 단순 노란색 라인 추종
갈림길 기능 없이 노란 선의 중앙을 따라가는 단순한 코드
"""
import cv2
import numpy as np
import time
import os

# OpenCV 헤드리스 모드 설정
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# GPIO 설정
USE_GPIO = True
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
        print("[✓] GPIO initialized")
    except Exception as e:
        print(f"[!] GPIO initialization failed: {e}")
        USE_GPIO = False


class SimpleMotor:
    """간단한 모터 제어"""

    def __init__(self):
        self.speed_forward = 70
        self.speed_turn = 50

    def forward(self, speed=None):
        """전진"""
        s = speed if speed else self.speed_forward
        if USE_GPIO:
            GPIO.output(IN1, True)
            GPIO.output(IN2, False)
            GPIO.output(IN3, True)
            GPIO.output(IN4, False)
            pwmA.ChangeDutyCycle(s)
            pwmB.ChangeDutyCycle(s)

    def left(self, speed=None):
        """좌회전"""
        s = speed if speed else self.speed_turn
        if USE_GPIO:
            GPIO.output(IN1, True)
            GPIO.output(IN2, False)
            GPIO.output(IN3, False)
            GPIO.output(IN4, True)
            pwmA.ChangeDutyCycle(s)
            pwmB.ChangeDutyCycle(s)

    def right(self, speed=None):
        """우회전"""
        s = speed if speed else self.speed_turn
        if USE_GPIO:
            GPIO.output(IN1, False)
            GPIO.output(IN2, True)
            GPIO.output(IN3, True)
            GPIO.output(IN4, False)
            pwmA.ChangeDutyCycle(s)
            pwmB.ChangeDutyCycle(s)

    def stop(self):
        """정지"""
        if USE_GPIO:
            GPIO.output(IN1, False)
            GPIO.output(IN2, False)
            GPIO.output(IN3, False)
            GPIO.output(IN4, False)
            pwmA.ChangeDutyCycle(0)
            pwmB.ChangeDutyCycle(0)

    def cleanup(self):
        """정리"""
        self.stop()
        if USE_GPIO:
            try:
                pwmA.stop()
                pwmB.stop()
                GPIO.cleanup()
            except:
                pass


def init_camera():
    """카메라 초기화"""
    try:
        from picamera2 import Picamera2
        print("[INFO] Initializing camera...")

        picam2 = Picamera2()
        config = picam2.create_preview_configuration(
            main={"format": "RGB888", "size": (640, 480)}
        )
        picam2.configure(config)
        picam2.start()

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
        print(f"[✗] Camera initialization failed: {e}")
        return None


def detect_yellow_line_center(frame):
    """
    노란 선의 중심 위치를 감지
    Returns:
        center_x: 노란 선의 중심 X 좌표 (0~640)
        found: 노란 선을 찾았는지 여부
        pixels: 감지된 픽셀 수
    """
    h, w = frame.shape[:2]

    # ROI 설정 (화면 하단 30% - 더 넓게)
    roi_height = int(h * 0.30)
    roi = frame[h - roi_height:h, :]

    # HSV 변환
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # 노란색 범위
    lower_yellow = np.array([20, 80, 80])
    upper_yellow = np.array([35, 255, 255])

    # 마스크 생성
    mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

    # 노이즈 제거
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.erode(mask, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=2)

    # 픽셀 수 확인
    pixels = cv2.countNonZero(mask)

    if pixels < 100:  # 노란 선을 못 찾음
        return w // 2, False, pixels

    # 모멘트를 이용한 중심점 계산
    moments = cv2.moments(mask)

    if moments['m00'] > 0:
        center_x = int(moments['m10'] / moments['m00'])
        return center_x, True, pixels
    else:
        return w // 2, False, pixels


def calculate_steering(center_x, frame_width):
    """
    조향 방향 계산
    Returns:
        action: 'forward', 'left', 'right', 'slight_left', 'slight_right'
    """
    frame_center = frame_width // 2
    error = center_x - frame_center

    # 편차에 따른 조향 결정
    if abs(error) < 50:  # 중앙 (±50 픽셀)
        return 'forward'
    elif abs(error) < 150:  # 약간 벗어남 (50~150 픽셀)
        if error > 0:
            return 'slight_right'
        else:
            return 'slight_left'
    else:  # 많이 벗어남 (150 픽셀 이상)
        if error > 0:
            return 'right'
        else:
            return 'left'


def main():
    """메인 루프"""
    print("=" * 60)
    print(" Simple Yellow Line Follower")
    print("=" * 60)
    print("[INFO] Press Ctrl+C to stop")
    print()

    # 초기화
    motor = SimpleMotor()
    camera = init_camera()

    if not camera:
        print("[✗] Cannot start without camera")
        return

    # 통계
    start_time = time.time()
    frame_count = 0
    search_count = 0

    try:
        while True:
            ret, frame = camera.read()
            if not ret:
                print("[ERROR] Failed to read frame")
                break

            frame_count += 1
            h, w = frame.shape[:2]

            # 노란 선 중심 감지
            center_x, found, pixels = detect_yellow_line_center(frame)

            if found:
                # 라인을 찾음 - 조향 계산
                search_count = 0
                action = calculate_steering(center_x, w)

                if action == 'forward':
                    motor.forward()
                    print("[MOTOR] FORWARD")  # 디버그
                elif action == 'slight_left':
                    motor.left(speed=45)
                    print("[MOTOR] SLIGHT_LEFT")  # 디버그
                elif action == 'slight_right':
                    motor.right(speed=45)
                    print("[MOTOR] SLIGHT_RIGHT")  # 디버그
                elif action == 'left':
                    motor.left()
                    print("[MOTOR] LEFT")  # 디버그
                elif action == 'right':
                    motor.right()
                    print("[MOTOR] RIGHT")  # 디버그

                # 상태 출력 (3초마다)
                if frame_count % 90 == 0:
                    runtime = int(time.time() - start_time)
                    fps = frame_count / max(runtime, 1)
                    error = center_x - (w // 2)
                    print(f"[{runtime:4d}s] Center:{center_x:3d} Error:{error:+4d} Pixels:{pixels:4d} | {action:12s} | FPS:{fps:.1f}")

            else:
                # 라인을 못 찾음 - 검색 모드
                search_count += 1

                if search_count < 5:
                    motor.stop()
                elif search_count < 30:
                    motor.right(speed=40)  # 천천히 오른쪽으로 회전
                elif search_count < 60:
                    motor.left(speed=40)   # 천천히 왼쪽으로 회전
                else:
                    motor.stop()
                    if search_count >= 100:
                        search_count = 0

                if frame_count % 30 == 0:
                    print(f"[SEARCH] Looking for yellow line... ({search_count})")

            time.sleep(0.03)  # 약 30 FPS

    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user")

    finally:
        # 종료 처리
        runtime = int(time.time() - start_time)
        print("\n" + "=" * 60)
        print(" Session Summary")
        print("=" * 60)
        print(f"Runtime: {runtime}s")
        print(f"Total frames: {frame_count}")
        print(f"Average FPS: {frame_count/max(runtime, 1):.1f}")
        print("=" * 60)

        motor.cleanup()
        camera.release()
        print("[✓] Cleanup complete")


if __name__ == "__main__":
    main()
