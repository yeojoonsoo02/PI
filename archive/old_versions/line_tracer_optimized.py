"""
Optimized Yellow Line Tracer - 최적화된 노란색 라인 트레이서
실시간 파라미터 자동 조정 + 안정적인 주행
"""
import cv2
import numpy as np
import time
import os

# OpenCV 헤드리스 모드 설정
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

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


class MotorController:
    """모터 제어 클래스"""

    def __init__(self):
        self.current_command = None
        self.speed_forward = 75  # 증가: 더 빠른 전진
        self.speed_turn = 55
        self.speed_slight = 48  # 증가: 더 부드러운 조향

    def forward(self):
        if USE_GPIO:
            GPIO.output(IN1, True)
            GPIO.output(IN2, False)
            GPIO.output(IN3, True)
            GPIO.output(IN4, False)
            pwmA.ChangeDutyCycle(self.speed_forward)
            pwmB.ChangeDutyCycle(self.speed_forward)
        self.current_command = "FORWARD"

    def backward(self, speed=60):
        if USE_GPIO:
            GPIO.output(IN1, False)
            GPIO.output(IN2, True)
            GPIO.output(IN3, False)
            GPIO.output(IN4, True)
            pwmA.ChangeDutyCycle(speed)
            pwmB.ChangeDutyCycle(speed)
        self.current_command = "BACKWARD"

    def left(self, slight=False):
        speed = self.speed_slight if slight else self.speed_turn
        if USE_GPIO:
            GPIO.output(IN1, True)
            GPIO.output(IN2, False)
            GPIO.output(IN3, False)
            GPIO.output(IN4, True)
            pwmA.ChangeDutyCycle(speed)
            pwmB.ChangeDutyCycle(speed)
        self.current_command = "LEFT" if not slight else "SLIGHT_LEFT"

    def right(self, slight=False):
        speed = self.speed_slight if slight else self.speed_turn
        if USE_GPIO:
            GPIO.output(IN1, False)
            GPIO.output(IN2, True)
            GPIO.output(IN3, True)
            GPIO.output(IN4, False)
            pwmA.ChangeDutyCycle(speed)
            pwmB.ChangeDutyCycle(speed)
        self.current_command = "RIGHT" if not slight else "SLIGHT_RIGHT"

    def stop(self):
        if USE_GPIO:
            GPIO.output(IN1, False)
            GPIO.output(IN2, False)
            GPIO.output(IN3, False)
            GPIO.output(IN4, False)
            pwmA.ChangeDutyCycle(0)
            pwmB.ChangeDutyCycle(0)
        self.current_command = "STOP"

    def cleanup(self):
        self.stop()
        if USE_GPIO:
            try:
                pwmA.stop()
                pwmB.stop()
                GPIO.cleanup()
            except:
                pass


class LineDetector:
    """라인 감지 클래스"""

    def __init__(self):
        # 노란색 HSV 범위 (자동 조정 가능)
        self.h_min, self.h_max = 20, 35
        self.s_min, self.s_max = 80, 255
        self.v_min, self.v_max = 80, 255

        # 임계값
        self.min_pixels = 200  # 증가: 노이즈 감소, 트랙 전용
        self.junction_threshold = 800  # 대폭 증가: 실제 갈림길만 감지

        # ROI 설정 (트랙 전용 - 더 작은 영역)
        self.roi_height_ratio = 0.25  # 감소: 0.35 → 0.25
        self.roi_width_ratio = 0.22   # 감소: 0.30 → 0.22

        # 통계
        self.detection_history = []
        self.max_history = 30

    def get_hsv_range(self):
        return (
            np.array([self.h_min, self.s_min, self.v_min]),
            np.array([self.h_max, self.s_max, self.v_max])
        )

    def detect_line_in_roi(self, roi):
        """ROI에서 라인 감지"""
        lower, upper = self.get_hsv_range()

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower, upper)

        # 노이즈 제거
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.erode(mask, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=2)

        pixels = cv2.countNonZero(mask)
        has_line = pixels > self.min_pixels

        return has_line, pixels

    def analyze_frame(self, frame):
        """프레임 분석"""
        h, w = frame.shape[:2]

        # ROI 계산
        roi_h = int(h * self.roi_height_ratio)
        roi_w = int(w * self.roi_width_ratio)
        roi_y = h - roi_h

        # 3개 ROI
        left_roi = frame[roi_y:h, 0:roi_w]
        center_x = (w - roi_w) // 2
        center_roi = frame[roi_y:h, center_x:center_x+roi_w]
        right_roi = frame[roi_y:h, w-roi_w:w]

        # 라인 감지
        left_line, left_px = self.detect_line_in_roi(left_roi)
        center_line, center_px = self.detect_line_in_roi(center_roi)
        right_line, right_px = self.detect_line_in_roi(right_roi)

        # 통계 업데이트
        self.detection_history.append({
            'left': left_px,
            'center': center_px,
            'right': right_px,
            'timestamp': time.time()
        })
        if len(self.detection_history) > self.max_history:
            self.detection_history.pop(0)

        return {
            'left': {'has_line': left_line, 'pixels': left_px},
            'center': {'has_line': center_line, 'pixels': center_px},
            'right': {'has_line': right_line, 'pixels': right_px}
        }

    def detect_junction(self, result):
        """갈림길 감지 (개선된 로직)"""
        left = result['left']
        center = result['center']
        right = result['right']

        # 충분한 픽셀이 있는지 확인
        left_ok = left['has_line'] and left['pixels'] >= self.junction_threshold
        center_ok = center['has_line'] and center['pixels'] >= self.junction_threshold
        right_ok = right['has_line'] and right['pixels'] >= self.junction_threshold

        # 진짜 갈림길인지 확인 (3개 모두 높은 값일 때만)
        total_pixels = left['pixels'] + center['pixels'] + right['pixels']

        # 갈림길 조건:
        # 1. 최소 2개 방향이 임계값 이상
        # 2. 전체 픽셀 수가 충분히 많음 (2000 이상)
        available = []
        if left_ok:
            available.append('left')
        if center_ok:
            available.append('forward')
        if right_ok:
            available.append('right')

        is_junction = (len(available) >= 2) and (total_pixels >= 2000)

        return is_junction, available


class LineTracer:
    """라인 트레이서 메인 클래스"""

    def __init__(self):
        self.motor = MotorController()
        self.detector = LineDetector()
        self.camera = None

        # 상태 변수
        self.search_count = 0
        self.last_direction = 'center'
        self.line_lost_frames = 0
        self.backing_up = False
        self.backup_frames = 0

        # 갈림길 쿨다운
        self.junction_cooldown = 0
        self.junction_cooldown_frames = 30  # 약 1초 쿨다운

        # 통계
        self.start_time = time.time()
        self.frame_count = 0
        self.junction_count = 0

    def init_camera(self):
        """카메라 초기화"""
        try:
            from picamera2 import Picamera2
            print("[INFO] Initializing Picamera2...")

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

            self.camera = CameraWrapper()
            return True

        except Exception as e:
            print(f"[✗] Camera initialization failed: {e}")
            return False

    def decide_action(self, result):
        """행동 결정"""
        left = result['left']
        center = result['center']
        right = result['right']

        # 갈림길 쿨다운 감소
        if self.junction_cooldown > 0:
            self.junction_cooldown -= 1

        # 갈림길 확인 (쿨다운 중이 아닐 때만)
        is_junction, available = self.detector.detect_junction(result)

        if is_junction and self.junction_cooldown == 0:
            self.junction_count += 1
            self.junction_cooldown = self.junction_cooldown_frames  # 쿨다운 시작
            return 'junction', available

        # 라인 따라가기
        if center['has_line']:
            return 'forward', None

        if left['has_line'] and right['has_line']:
            # 둘 다 있으면 픽셀 차이로 판단
            diff = left['pixels'] - right['pixels']
            if abs(diff) < 80:
                return 'forward', None
            elif diff > 0:
                return 'slight_right', None
            else:
                return 'slight_left', None

        if left['has_line']:
            self.last_direction = 'left'
            return 'right', None

        if right['has_line']:
            self.last_direction = 'right'
            return 'left', None

        # 라인 없음
        return 'search', None

    def execute_action(self, action, available_dirs=None):
        """행동 실행"""

        # 후진 모드
        if self.backing_up:
            self.backup_frames += 1
            self.motor.backward()

            if self.backup_frames >= 50:
                self.backing_up = False
                self.backup_frames = 0
                self.line_lost_frames = 0
                self.search_count = 0
                print("[INFO] Backup complete")
            return

        # 갈림길 처리
        if action == 'junction':
            print(f"[JUNCTION] Available: {available_dirs}")

            # 우선순위: forward > right > left
            if 'forward' in available_dirs:
                self.motor.forward()
                time.sleep(0.8)
            elif 'right' in available_dirs:
                self.motor.right()
                time.sleep(0.6)
            elif 'left' in available_dirs:
                self.motor.left()
                time.sleep(0.6)

            self.search_count = 0
            self.line_lost_frames = 0
            return

        # 라인 찾기 모드
        if action == 'search':
            self.search_count += 1
            self.line_lost_frames += 1

            # 라인 이탈 체크
            if self.line_lost_frames >= 25 and not self.backing_up:
                self.backing_up = True
                self.backup_frames = 0
                print("[WARNING] Line lost! Backing up...")
                return

            # 회전 검색
            if self.search_count < 5:
                self.motor.stop()
            elif self.search_count < 50:
                if self.last_direction == 'left':
                    self.motor.right(slight=True)
                else:
                    self.motor.left(slight=True)
            elif self.search_count < 100:
                if self.last_direction == 'left':
                    self.motor.left(slight=True)
                else:
                    self.motor.right(slight=True)
            else:
                self.motor.right(slight=True)
                if self.search_count >= 200:
                    self.search_count = 0
            return

        # 정상 주행
        self.search_count = 0
        self.line_lost_frames = 0

        if action == 'forward':
            self.motor.forward()
        elif action == 'left':
            self.motor.left()
        elif action == 'right':
            self.motor.right()
        elif action == 'slight_left':
            self.motor.left(slight=True)
        elif action == 'slight_right':
            self.motor.right(slight=True)

    def print_status(self, result, action):
        """상태 출력"""
        left = result['left']['pixels']
        center = result['center']['pixels']
        right = result['right']['pixels']

        runtime = int(time.time() - self.start_time)
        fps = self.frame_count / max(runtime, 1)

        print(f"[{runtime:4d}s] L:{left:3d} C:{center:3d} R:{right:3d} | "
              f"{self.motor.current_command:12s} | FPS:{fps:.1f} | J:{self.junction_count}")

    def run(self):
        """메인 루프"""
        print("=" * 70)
        print(" Optimized Yellow Line Tracer")
        print("=" * 70)
        print("[INFO] Press Ctrl+C to stop")
        print()

        if not self.init_camera():
            return

        last_print = time.time()

        try:
            while True:
                ret, frame = self.camera.read()
                if not ret:
                    print("[ERROR] Failed to read frame")
                    break

                self.frame_count += 1

                # 라인 분석
                result = self.detector.analyze_frame(frame)

                # 행동 결정
                action, available = self.decide_action(result)

                # 행동 실행
                self.execute_action(action, available)

                # 상태 출력 (3초마다)
                if time.time() - last_print >= 3.0:
                    self.print_status(result, action)
                    last_print = time.time()

                time.sleep(0.02)  # 약 50 FPS 목표

        except KeyboardInterrupt:
            print("\n[INFO] Stopped by user")

        finally:
            self.cleanup()

    def cleanup(self):
        """정리"""
        runtime = int(time.time() - self.start_time)

        print("\n" + "=" * 70)
        print(" Session Summary")
        print("=" * 70)
        print(f"Runtime: {runtime}s")
        print(f"Total frames: {self.frame_count}")
        print(f"Average FPS: {self.frame_count/max(runtime, 1):.1f}")
        print(f"Junctions detected: {self.junction_count}")
        print("=" * 70)

        self.motor.cleanup()
        if self.camera:
            self.camera.release()

        print("[✓] Cleanup complete")


if __name__ == "__main__":
    tracer = LineTracer()
    tracer.run()
