# 파일: /home/easo6/AI_CAR/manual_drive.py
import cv2
import time

# ====== 모터 제어(테스트용 프린트 ↔ 실제 GPIO 전환) ======
USE_GPIO = False  # 실제 연결 시 True로 변경
if USE_GPIO:
    import RPi.GPIO as GPIO
    # 예시 핀맵(모터 드라이버 L298N 등) -- 네 보드에 맞게 수정
    IN1, IN2, IN3, IN4, ENA, ENB = 17, 18, 22, 23, 24, 25
    GPIO.setmode(GPIO.BCM)
    for p in (IN1,IN2,IN3,IN4,ENA,ENB):
        GPIO.setup(p, GPIO.OUT)
    pwmA = GPIO.PWM(ENA, 1000); pwmA.start(0)
    pwmB = GPIO.PWM(ENB, 1000); pwmB.start(0)

def motor_forward(speed=60):
    if USE_GPIO:
        # 좌/우 모터 정방향 (예시)
        GPIO.output(IN1, True); GPIO.output(IN2, False)
        GPIO.output(IN3, True); GPIO.output(IN4, False)
        pwmA.ChangeDutyCycle(speed); pwmB.ChangeDutyCycle(speed)
    else:
        print(f"[MOTOR] FORWARD speed={speed}")

def motor_left(speed=45):
    if USE_GPIO:
        # 좌회전(좌 느리게/우 빠르게) 예시
        GPIO.output(IN1, True); GPIO.output(IN2, False)
        GPIO.output(IN3, False); GPIO.output(IN4, True)
        pwmA.ChangeDutyCycle(speed); pwmB.ChangeDutyCycle(speed)
    else:
        print(f"[MOTOR] LEFT speed={speed}")

def motor_right(speed=45):
    if USE_GPIO:
        # 우회전(좌 빠르게/우 느리게) 예시
        GPIO.output(IN1, False); GPIO.output(IN2, True)
        GPIO.output(IN3, True); GPIO.output(IN4, False)
        pwmA.ChangeDutyCycle(speed); pwmB.ChangeDutyCycle(speed)
    else:
        print(f"[MOTOR] RIGHT speed={speed}")

def motor_stop():
    if USE_GPIO:
        GPIO.output(IN1, False); GPIO.output(IN2, False)
        GPIO.output(IN3, False); GPIO.output(IN4, False)
        pwmA.ChangeDutyCycle(0); pwmB.ChangeDutyCycle(0)
    else:
        print("[MOTOR] STOP")

# ====== 카메라 열기 (VideoCapture 우선, 실패시 Picamera2 시도) ======
def open_camera():
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        return cap
    try:
        from picamera2 import Picamera2
        import numpy as np
        picam2 = Picamera2()
        picam2.configure(picam2.create_preview_configuration(main={"format":"RGB888"}))
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

def main():
    cap = open_camera()
    speed = 60
    print("[INFO] Arrow Keys or WASD to drive. SPACE: stop, +/-: speed, q/ESC: quit")
    try:
        while True:
            ret, frame = cap.read()
            if not ret: break
            cv2.putText(frame, f"speed={speed}", (10,30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 2)
            cv2.imshow("manual", frame)
            key = cv2.waitKey(1) & 0xFFFF

            if key in (27, ord('q')):  # ESC or q
                motor_stop(); break
            elif key in (ord('w'), 2490368):  # up
                motor_forward(speed)
            elif key in (ord('a'), 2424832):  # left
                motor_left(int(speed*0.8))
            elif key in (ord('d'), 2555904):  # right
                motor_right(int(speed*0.8))
            elif key in (ord('s'), 2621440):  # down
                motor_stop()
            elif key == ord(' '):
                motor_stop()
            elif key in (ord('+'), ord('=')):
                speed = min(100, speed+5)
            elif key in (ord('-'), ord('_')):
                speed = max(20, speed-5)
    finally:
        cap.release()
        cv2.destroyAllWindows()
        motor_stop()
        if USE_GPIO:
            GPIO.cleanup()

if __name__ == "__main__":
    main()