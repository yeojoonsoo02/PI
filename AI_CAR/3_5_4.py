from gpiozero import Button
from gpiozero import DigitalOutputDevice
from gpiozero import PWMOutputDevice
import time

SW1 = Button(5, pull_up=False )
SW2 = Button(6, pull_up=False )
SW3 = Button(13, pull_up=False )
SW4 = Button(19, pull_up=False )

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
    PWMA.value = speed
    BIN1.value = 0
    BIN2.value = 1
    PWMB.value = speed
    
def motor_right(speed):
    AIN1.value = 0
    AIN2.value = 1
    PWMA.value = speed
    BIN1.value = 1
    BIN2.value = 0
    PWMB.value = speed

def motor_stop():
    AIN1.value = 0
    AIN2.value = 1
    PWMA.value = 0.0
    BIN1.value = 0
    BIN2.value = 1
    PWMB.value = 0.0

try:
    while True:
        if SW1.is_pressed == True:
            print("go")
            motor_go(0.5)
        elif SW2.is_pressed == True:
            print("right")
            motor_right(0.5)
        elif SW3.is_pressed == True:
            print("left")
            motor_left(0.5)
        elif SW4.is_pressed == True:
            print("back")
            motor_back(0.5)
        else:
            print("stop")
            motor_stop()
        
        time.sleep(0.1)
            
except KeyboardInterrupt:
    pass

PWMA.value = 0.0
PWMB.value = 0.0