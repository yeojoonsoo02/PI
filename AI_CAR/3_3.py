from gpiozero import  TonalBuzzer
import time

BUZZER = TonalBuzzer(12)

try:
    while True:
        BUZZER.play(261)
        time.sleep(1.0)
        BUZZER.stop()
        time.sleep(1.0)

except KeyboardInterrupt:
    pass

BUZZER.stop()