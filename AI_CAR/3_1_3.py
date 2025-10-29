from gpiozero import LED
import time

led1 = LED(26)
led2 = LED(16)
led3 = LED(20)
led4 = LED(21)

try:
    while True:
        led1.on()
        led2.on()
        led3.on()
        led4.on()
        time.sleep(1.0)
        led1.off()
        led2.off()
        led3.off()
        led4.off()
        time.sleep(1.0)

except KeyboardInterrupt:
    pass

led1.off()
led2.off()
led3.off()
led4.off()