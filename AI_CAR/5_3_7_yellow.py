import mycamera
import cv2
import numpy as np
from gpiozero import DigitalOutputDevice
from gpiozero import PWMOutputDevice

PWMA = PWMOutputDevice(18)
AIN1 = DigitalOutputDevice(22)
AIN2 = DigitalOutputDevice(27)

PWMB = PWMOutputDevice(23)
BIN1 = DigitalOutputDevice(25)
BIN2 = DigitalOutputDevice(24)

def motor_go(speed):
    AIN1.value = 0
    AIN2.value = 1
    PWMA.value = speed
    BIN1.value = 0
    BIN2.value = 1
    PWMB.value = speed

def motor_back(speed):
    AIN1.value = 1
    AIN2.value = 0
    PWMA.value = speed
    BIN1.value = 1
    BIN2.value = 0
    PWMB.value = speed

def motor_left(speed):
    AIN1.value = 1
    AIN2.value = 0
    PWMA.value = 0.0
    BIN1.value = 0
    BIN2.value = 1
    PWMB.value = speed

def motor_right(speed):
    AIN1.value = 0
    AIN2.value = 1
    PWMA.value = speed
    BIN1.value = 1
    BIN2.value = 0
    PWMB.value = 0.0

def main():
    camera = mycamera.MyPiCamera(320,240)

    while( camera.isOpened() ):
        _, image = camera.read()
        image = cv2.flip(image,-1)
        cv2.imshow('normal',image)

        height, width, _ = image.shape
        crop_img = image[height //2 :, :]

        # ===== 여기부터 변경 =====
        # BGR을 HSV로 변환
        hsv = cv2.cvtColor(crop_img, cv2.COLOR_BGR2HSV)

        # 노란색 범위 설정 (HSV)
        # 밝은 노란색: H=20-30, S=100-255, V=100-255
        lower_yellow = np.array([20, 100, 100])
        upper_yellow = np.array([30, 255, 255])

        # 노란색 마스크 생성
        mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

        # 노이즈 제거 (기존과 동일)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        cv2.imshow('mask',mask)
        # ===== 여기까지 변경 =====

        contours,hierarchy = cv2.findContours(mask.copy(), 1, cv2.CHAIN_APPROX_NONE)

        if len(contours) > 0:
            c = max(contours, key=cv2.contourArea)
            M = cv2.moments(c)

            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])

            if cx >= 190 and cx <= 250:
                print("Turn Left!")
                motor_left(0.3)
            elif cx >= 80 and cx <= 130:
                print("Turn Right")
                motor_right(0.3)
            else:
                print("go")
                motor_go(0.3)

        if cv2.waitKey(1) == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
    PWMA.value = 0.0
    PWMB.value = 0.0
