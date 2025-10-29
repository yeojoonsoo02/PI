from gpiozero import  TonalBuzzer
import time

BUZZER = TonalBuzzer(12)

try:
    while True:
        BUZZER.play(391)
        time.sleep(0.2)
        
        BUZZER.stop()
        time.sleep(0.1)
        
        BUZZER.play(391)
        time.sleep(0.2)
        
        BUZZER.stop()
        time.sleep(0.1)
        
        BUZZER.stop()
        time.sleep(2.0)

except KeyboardInterrupt:
    pass

BUZZER.stop()


