from gpiozero import Button
import time

SW1 = Button(5, pull_up=False )

try:
    while True:
        sw1Value = SW1.is_pressed
        print(sw1Value)
        time.sleep(0.1)

except KeyboardInterrupt:
    pass
