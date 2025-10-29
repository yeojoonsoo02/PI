from gpiozero import LED
import time

led1 = LED(26)

try:
    while True:
        led1.on()
        time.sleep(1.0)
        led1.off()
        time.sleep(1.0)

except KeyboardInterrupt:
    pass

led1.off()