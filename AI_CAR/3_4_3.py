from gpiozero import DigitalOutputDevice
from gpiozero import PWMOutputDevice
import time

PWMA = PWMOutputDevice(18)
AIN1 = DigitalOutputDevice(22)
AIN2 = DigitalOutputDevice(27)

try:
    while True:
        AIN1.value = 0
        AIN2.value = 1
        PWMA.value = 0.5 # 0.0~1.0 speed
        time.sleep(1.0)
        
        AIN1.value = 0
        AIN2.value = 1
        PWMA.value = 0.0 # 0.0~1.0 speed
        time.sleep(1.0)
        
        AIN1.value = 1
        AIN2.value = 0
        PWMA.value = 0.5 # 0.0~1.0 speed
        time.sleep(1.0)
        
        AIN1.value = 1
        AIN2.value = 0
        PWMA.value = 0.0 # 0.0~1.0 speed
        time.sleep(1.0)
        
except KeyboardInterrupt:
    pass

PWMA.value = 0.0