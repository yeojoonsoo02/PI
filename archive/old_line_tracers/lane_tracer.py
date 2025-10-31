# 파일: /home/easo6/AI_CAR/lane_tracer.py
import cv2
import numpy as np

USE_GPIO = False  # 실제 연결시 True
if USE_GPIO:
    import RPi.GPIO as GPIO
    IN1, IN2, IN3, IN4, ENA, ENB = 17, 18, 22, 23, 24, 25
    GPIO.setmode(GPIO.BCM)
    for p in (IN1,IN2,IN3,IN4,ENA,ENB):
        GPIO.setup(p, GPIO.OUT)
    pwmA = GPIO.PWM(ENA, 1000); pwmA.start(0)
    pwmB = GPIO.PWM(ENB, 1000); pwmB.start(0)

def motor_forward(speed=65):
    if USE_GPIO:
        GPIO.output(IN1, True); GPIO.output(IN2, False)
        GPIO.output(IN3, True); GPIO.output(IN4, False)
        pwmA.ChangeDutyCycle(speed); pwmB.ChangeDutyCycle(speed)
    else:
        print(f"[MOTOR] FORWARD {speed}")

def motor_left(speed=50):
    if USE_GPIO:
        GPIO.output(IN1, True); GPIO.output(IN2, False)
        GPIO.output(IN3, False); GPIO.output(IN4, True)
        pwmA.ChangeDutyCycle(speed); pwmB.ChangeDutyCycle(speed)
    else:
        print(f"[MOTOR] LEFT {speed}")

def motor_right(speed=50):
    if USE_GPIO:
        GPIO.output(IN1, False); GPIO.output(IN2, True)
        GPIO.output(IN3, True); GPIO.output(IN4, False)
        pwmA.ChangeDutyCycle(speed); pwmB.ChangeDutyCycle(speed)
    else:
        print(f"[MOTOR] RIGHT {speed}")

def motor_stop():
    if USE_GPIO:
        GPIO.output(IN1, False); GPIO.output(IN2, False)
        GPIO.output(IN3, False); GPIO.output(IN4, False)
        pwmA.ChangeDutyCycle(0); pwmB.ChangeDutyCycle(0)
    else:
        print("[MOTOR] STOP")

def open_camera():
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        return cap
    try:
        from picamera2 import Picamera2
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

def decide_command(frame, roi_ratio=0.4, thresh=150, dead_ratio=0.03):
    h, w = frame.shape[:2]
    roi_y = int(h*(1.0 - roi_ratio))  # 하단 roi_ratio 사용
    roi = frame[roi_y:h, 0:w]

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    _, th = cv2.threshold(blur, thresh, 255, cv2.THRESH_BINARY_INV)

    M = cv2.moments(th)
    if M["m00"] == 0:
        return "stop", roi, th, None

    cx = int(M["m10"]/M["m00"])
    center = w // 2
    offset = cx - center
    dead = int(w * dead_ratio)

    if offset > dead:
        cmd = "right"
    elif offset < -dead:
        cmd = "left"
    else:
        cmd = "straight"
    return cmd, roi, th, (cx, center, offset, dead)

def main():
    cap = open_camera()
    print("[INFO] q/ESC 종료. 튜닝: thresh(키 1/2), ROI(키 3/4)")
    thresh = 150
    roi_ratio = 0.4
    try:
        while True:
            ret, frame = cap.read()
            if not ret: break

            cmd, roi, th, info = decide_command(frame, roi_ratio, thresh)
            if cmd == "straight": motor_forward(65)
            elif cmd == "left":   motor_left(50)
            elif cmd == "right":  motor_right(50)
            else:                 motor_stop()

            # 디버그 오버레이
            h, w = frame.shape[:2]
            y = int(h*(1.0 - roi_ratio))
            cv2.line(frame, (0,y), (w,y), (0,255,255), 2)
            if info:
                cx, center, offset, dead = info
                cv2.circle(frame, (cx, y+10), 6, (0,0,255), -1)
                cv2.line(frame, (center, y-10), (center, y+10), (255,0,0), 2)
                cv2.putText(frame, f"offset={offset}", (10,30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 2)
            cv2.putText(frame, f"cmd={cmd} thresh={thresh} roi={roi_ratio:.2f}",
                        (10,60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

            cv2.imshow("lane", frame)
            cv2.imshow("thresh", th)

            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q')):  # ESC,q
                motor_stop(); break
            elif key == ord('1'):
                thresh = max(60, thresh-5)   # 어두울수록 임계값 낮추기
            elif key == ord('2'):
                thresh = min(220, thresh+5)  # 밝을수록 임계값 높이기
            elif key == ord('3'):
                roi_ratio = min(0.7, roi_ratio+0.02)  # ROI 더 얕게(상단으로)
            elif key == ord('4'):
                roi_ratio = min(0.9, max(0.2, roi_ratio-0.02))  # ROI 더 깊게(하단만)

    finally:
        cap.release()
        cv2.destroyAllWindows()
        motor_stop()
        if USE_GPIO:
            GPIO.cleanup()

if __name__ == "__main__":
    main()