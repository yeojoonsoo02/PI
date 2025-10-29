from gpiozero import  TonalBuzzer
import time

BUZZER = TonalBuzzer(12)

try:
    while True:
        BUZZER.play(261) #do
        time.sleep(1.0)
        BUZZER.play(293) #le
        time.sleep(1.0)
        BUZZER.play(329) #mi
        time.sleep(1.0)
        BUZZER.play(349) #fa
        time.sleep(1.0)
        BUZZER.play(391) #sol
        time.sleep(1.0)
        BUZZER.play(440) #la
        time.sleep(1.0)
        BUZZER.play(493) #si
        time.sleep(1.0)
        BUZZER.play(523) #5oc do~
        time.sleep(1.0)
        BUZZER.stop()
        time.sleep(1.0)

except KeyboardInterrupt:
    pass

BUZZER.stop()